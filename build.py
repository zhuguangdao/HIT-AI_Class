from collections import defaultdict
from html import escape
from json import loads
from pathlib import Path, PurePosixPath
from re import fullmatch, sub
from shutil import copy2, copytree, rmtree
from urllib.parse import quote, urlsplit, urlunsplit


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "site"
PDFS = ROOT / "pdfs"
RESTRICTED = ROOT / "restricted.json"
OUTPUT = ROOT / "dist"


def load_restricted():
    if not RESTRICTED.exists():
        return []

    entries = loads(RESTRICTED.read_text(encoding="utf-8-sig"))
    if not isinstance(entries, list):
        raise ValueError("restricted.json 必须是一个列表")

    documents = []
    for index, entry in enumerate(entries, start=1):
        prefix = f"restricted.json 第 {index} 条"
        if not isinstance(entry, dict):
            raise ValueError(f"{prefix}必须是一个对象")

        title = entry.get("title")
        course = entry.get("course", "")
        link = entry.get("url")
        if not isinstance(title, str) or not title.strip():
            raise ValueError(f"{prefix}的 title 不能为空")
        if not isinstance(course, str):
            raise ValueError(f"{prefix}的 course 必须是文本")
        course_parts = [part.strip() for part in course.strip().split("/")] if course.strip() else []
        if any(part in {"", ".", ".."} for part in course_parts):
            raise ValueError(f"{prefix}的 course 请填写课程名或「学期/课程名」")
        if not isinstance(link, str):
            raise ValueError(f"{prefix}需要填写飞书云空间的文件链接")

        target = urlsplit(link.strip())
        if (
            target.scheme != "https"
            or not fullmatch(r"(?:[a-z0-9-]+\.)*feishu\.cn", target.netloc.lower())
            or not fullmatch(r"/file/[A-Za-z0-9_-]+/?", target.path)
        ):
            raise ValueError(f"{prefix}需要使用 https://…feishu.cn/file/… 格式的飞书文件链接")
        url = urlunsplit(("https", target.netloc.lower(), target.path.rstrip("/"), "", ""))
        documents.append((PurePosixPath(*course_parts), title.strip(), render_restricted(title.strip(), url)))
    return documents


def format_size(size):
    if size >= 1024 ** 2:
        return f"{size / 1024 ** 2:.1f} MB"
    if size >= 1024:
        return f"{size / 1024:.0f} KB"
    return f"{size} B"


def add_pdf(relative_path):
    source = PDFS / relative_path
    destination = OUTPUT / "pdfs" / relative_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    copy2(source, destination)

    href = "./pdfs/" + quote(relative_path.as_posix())
    size = format_size(source.stat().st_size)
    title = escape(relative_path.stem)
    actions = f"""
          <a href="{href}" target="_blank" rel="noopener" aria-label="预览 {title}（新标签页）">预览<span aria-hidden="true">↗</span></a>
          <a href="{href}" download aria-label="下载 {title}">下载<span aria-hidden="true">↓</span></a>"""
    return render_document(title, size, actions)


def render_restricted(title, url):
    title = escape(title)
    href = escape(url)
    actions = f"""
          <a class="request-link" href="{href}" target="_blank" rel="noopener noreferrer" aria-label="申请访问 {title}（在飞书中打开）">申请访问<span aria-hidden="true">↗</span></a>"""
    return render_document(title, "需批准", actions)


def render_document(title, detail, actions):
    return f"""
      <li class="document">
        <span class="document-icon" aria-hidden="true">PDF</span>
        <div class="document-info">
          <h4 class="document-title">{title}</h4>
          <span class="document-detail">{detail}</span>
        </div>
        <div class="document-actions">{actions}
        </div>
      </li>"""


def render_catalog(groups):
    navigation = []
    sections = []
    parents = sorted(groups, key=lambda parent: (not parent.parts, parent.as_posix().casefold()))
    for index, parent in enumerate(parents, start=1):
        course_id = f"course-{index}"
        course_name = escape(" / ".join(parent.parts) or "未分类")
        documents = groups[parent]
        count = len(documents)
        navigation.append(
            f'<li><a href="#{course_id}"><span>{course_name}</span><small>{count}</small></a></li>'
        )
        rows = "\n".join(row for _, row in sorted(documents, key=lambda document: document[0].casefold()))
        sections.append(f"""
    <section class="course" id="{course_id}" aria-labelledby="{course_id}-title">
      <header class="course-header">
        <h3 id="{course_id}-title">{course_name}</h3>
        <span class="course-count">{count} 份</span>
      </header>
      <ul class="documents" role="list">{rows}
      </ul>
    </section>""")

    return "\n".join(navigation), "\n".join(sections)


def main():
    restricted = load_restricted()
    if OUTPUT.is_symlink():
        raise RuntimeError("dist must be an ordinary directory")
    if OUTPUT.exists():
        rmtree(OUTPUT)
    copytree(SOURCE, OUTPUT)

    groups = defaultdict(list)
    paths = sorted(PDFS.rglob("*"), key=lambda path: path.as_posix().casefold())
    for path in paths:
        relative_path = path.relative_to(PDFS)
        if path.suffix.lower() != ".pdf" or not path.is_file() or path.is_symlink():
            continue
        if any(part.startswith(".") for part in relative_path.parts):
            continue
        course = PurePosixPath(*relative_path.parent.parts)
        groups[course].append((relative_path.stem, add_pdf(relative_path)))

    for course, title, row in restricted:
        groups[course].append((title, row))

    navigation, sections = render_catalog(groups)
    count = sum(map(len, groups.values()))
    template = (SOURCE / "index.html").read_text(encoding="utf-8")
    replacements = {
        "<!-- NAVIGATION -->": navigation,
        "<!-- CATALOG -->": sections,
        "<!-- TOTAL -->": str(count),
        "<!-- SEARCH_STATE -->": "" if count else "hidden",
        "<!-- EMPTY_STATE -->": "hidden" if count else "",
        "<!-- NAVIGATION_STATE -->": "" if count else "hidden",
        "<!-- NAVIGATION_EMPTY -->": "hidden" if count else "",
        "<!-- ACCESS_STATE -->": "" if restricted else "hidden",
    }
    template = sub(r"<!-- [A-Z_]+ -->", lambda marker: replacements[marker.group()], template)
    (OUTPUT / "index.html").write_text(template, encoding="utf-8")
    print(f"Built {count} PDFs in {len(groups)} groups.")


if __name__ == "__main__":
    main()
