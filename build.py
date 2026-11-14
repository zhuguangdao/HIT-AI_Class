from collections import defaultdict
from html import escape
from itertools import groupby
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

LEVELS = {
    "undergraduate": ("本科生", {"本科", "本科生"}),
    "graduate": ("研究生", {"研究生", "硕士", "博士"}),
    "other": ("其他资料", set()),
}
PREVIEWABLE = {"pdf", "png", "jpg", "jpeg", "gif", "webp", "avif", "bmp", "ico", "txt", "log"}


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
            raise ValueError(f"{prefix}的 course 请填写如「本科/课程名」的目录路径")
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


def add_public_file(source, relative_path):
    destination = OUTPUT / "pdfs" / relative_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    copy2(source, destination)

    href = "./pdfs/" + quote(relative_path.as_posix())
    size = format_size(source.stat().st_size)
    file_type = relative_path.suffix.removeprefix(".").lower()
    title = escape(relative_path.name)
    preview = ""
    if file_type in PREVIEWABLE:
        preview = f'<a href="{href}" target="_blank" rel="noopener" aria-label="预览 {title}（新标签页）">预览<span aria-hidden="true">↗</span></a>'
    actions = f"""
          {preview}
          <a href="{href}" download aria-label="下载 {title}">下载<span aria-hidden="true">↓</span></a>"""
    return render_document(title, size, actions, file_type)


def render_restricted(title, url):
    title = escape(title)
    href = escape(url)
    actions = f"""
          <a class="request-link" href="{href}" target="_blank" rel="noopener noreferrer" aria-label="申请访问 {title}（在飞书中打开）">申请访问<span aria-hidden="true">↗</span></a>"""
    return render_document(title, "需批准", actions, "受限")


def render_document(title, detail, actions, file_type):
    label = escape(file_type.upper() or "文件")
    css_class = " document-icon--restricted" if file_type == "受限" else ""
    return f"""
      <li class="document">
        <span class="document-icon{css_class}">{label}</span>
        <div class="document-info">
          <strong class="document-title">{title}</strong>
          <span class="document-detail">{detail}</span>
        </div>
        <div class="document-actions">{actions}
        </div>
      </li>"""


def group_key(path):
    first, *rest = path.parts or ("",)
    for level, (_, aliases) in LEVELS.items():
        if first in aliases:
            return level, rest[0] if rest else "未分类", tuple(rest[1:])
    return "other", first or "未分类", tuple(rest)


def render_course(level, index, course, documents):
    course_id = f"{level}-course-{index}"
    course_name = escape(course)
    subgroup_html = []
    documents.sort(key=lambda item: (item[0], item[1].casefold(), item[1]))
    for parts, items in groupby(documents, key=lambda item: item[0]):
        label = escape(" / ".join(parts))
        heading = f'<h5 class="subgroup-title">{label}</h5>' if label else ""
        rows = "\n".join(row for _, _, row in items)
        subgroup_html.append(f"""
      <div class="subgroup">{heading}
        <ul class="documents" role="list">{rows}
        </ul>
      </div>""")

    navigation = f'<li><a href="#{course_id}">{course_name}</a></li>'
    section = f"""
    <section class="course" id="{course_id}" aria-labelledby="{course_id}-title">
      <header class="course-header">
        <h4 id="{course_id}-title">{course_name}</h4>
        <span class="course-count">{len(documents)} 份</span>
      </header>
      {''.join(subgroup_html)}
    </section>"""
    return navigation, section


def render_catalog(groups):
    navigation = []
    sections = []
    for level, (label, _) in LEVELS.items():
        courses = groups.get(level)
        if not courses:
            continue
        nav_items, course_sections = [], []
        for index, course in enumerate(sorted(courses, key=str.casefold), start=1):
            item, section = render_course(level, index, course, courses[course])
            nav_items.append(item)
            course_sections.append(section)
        count = sum(map(len, courses.values()))
        navigation.append(f"""
      <div class="level-nav" data-level="{level}">
        <a class="level-nav-title" href="#{level}">{label}<span aria-hidden="true">↘</span></a>
        <ul class="category-list" role="list">{''.join(nav_items)}</ul>
      </div>""")
        sections.append(f"""
    <section class="level" id="{level}" aria-labelledby="{level}-title">
      <header class="level-header">
        <h3 id="{level}-title">{label}</h3>
        <span class="level-count">{len(courses)} 门课程 · {count} 份资料</span>
      </header>
      {''.join(course_sections)}
    </section>""")
    return "".join(navigation), "".join(sections)


def main():
    restricted = load_restricted()
    if OUTPUT.is_symlink() or OUTPUT.resolve() != OUTPUT:
        raise RuntimeError("dist must be an ordinary directory")
    if OUTPUT.exists():
        rmtree(OUTPUT)
    copytree(SOURCE, OUTPUT)

    groups = defaultdict(lambda: defaultdict(list))
    paths = sorted(PDFS.rglob("*"), key=lambda path: path.as_posix().casefold())
    for path in paths:
        relative_path = path.relative_to(PDFS)
        if not path.is_file() or path.is_symlink():
            continue
        if any(part.startswith(".") or part == "__MACOSX" for part in relative_path.parts):
            continue
        if relative_path.as_posix().casefold() == "readme.md" or path.name.casefold() in {"thumbs.db", "desktop.ini"}:
            continue
        level, course, subgroup = group_key(relative_path.parent)
        groups[level][course].append((subgroup, relative_path.name, add_public_file(path, relative_path)))

    for folder, title, row in restricted:
        level, course, subgroup = group_key(folder)
        groups[level][course].append((subgroup, title, row))

    navigation, sections = render_catalog(groups)
    course_count = sum(map(len, groups.values()))
    count = sum(len(documents) for courses in groups.values() for documents in courses.values())
    template = (SOURCE / "index.html").read_text(encoding="utf-8")
    replacements = {
        "<!-- NAVIGATION -->": navigation,
        "<!-- CATALOG -->": sections,
        "<!-- TOTAL -->": str(count),
        "<!-- COURSE_TOTAL -->": str(course_count),
        "<!-- SEARCH_STATE -->": "" if count else "hidden",
        "<!-- EMPTY_STATE -->": "hidden" if count else "",
        "<!-- NAVIGATION_STATE -->": "" if count else "hidden",
        "<!-- ACCESS_STATE -->": "" if restricted else "hidden",
    }
    template = sub(r"<!-- [A-Z_]+ -->", lambda marker: replacements[marker.group()], template)
    (OUTPUT / "index.html").write_text(template, encoding="utf-8")
    print(f"Built {count} files in {course_count} courses.")


if __name__ == "__main__":
    main()
