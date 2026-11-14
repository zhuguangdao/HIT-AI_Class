const search = document.querySelector("#search");
const resultsCount = document.querySelector("#results-count");
const noResults = document.querySelector("#no-results");

const levels = [...document.querySelectorAll(".level")].map((section) => {
  const levelTitle = section.querySelector("h3").textContent;
  const navigation = document.querySelector(`.level-nav[data-level="${section.id}"]`);
  const courses = [...section.querySelectorAll(".course")].map((course) => {
    const courseTitle = course.querySelector("h4").textContent;
    const item = navigation.querySelector(`a[href="#${course.id}"]`).parentElement;
    const groups = [...course.querySelectorAll(".subgroup")].map((group) => {
      const groupTitle = group.querySelector(".subgroup-title")?.textContent || "";
      const documents = [...group.querySelectorAll(".document")].map((row) => ({
        row,
        text: [
          levelTitle,
          courseTitle,
          groupTitle,
          row.querySelector(".document-title").textContent,
          row.querySelector(".document-icon").textContent,
        ].join(" ").toLowerCase(),
      }));
      return { group, documents };
    });
    return { course, item, groups, count: course.querySelector(".course-count") };
  });
  return { section, navigation, courses, count: section.querySelector(".level-count") };
});

function filterCatalog() {
  const tokens = search.value.trim().toLowerCase().split(/\s+/).filter(Boolean);
  let visibleDocuments = 0;

  for (const level of levels) {
    let levelCount = 0;
    let courseTotal = 0;
    for (const course of level.courses) {
      let courseCount = 0;
      for (const { group, documents } of course.groups) {
        let groupCount = 0;
        for (const { row, text } of documents) {
          const match = tokens.every((token) => text.includes(token));
          row.hidden = !match;
          groupCount += Number(match);
        }
        group.hidden = groupCount === 0;
        courseCount += groupCount;
      }
      course.course.hidden = courseCount === 0;
      course.item.hidden = courseCount === 0;
      course.count.textContent = `${courseCount} 份`;
      courseTotal += Number(courseCount > 0);
      levelCount += courseCount;
    }
    level.section.hidden = levelCount === 0;
    level.navigation.hidden = levelCount === 0;
    level.count.textContent = `${courseTotal} 门课程 · ${levelCount} 份资料`;
    visibleDocuments += levelCount;
  }

  document.querySelector(".sidebar").hidden = visibleDocuments === 0;
  resultsCount.textContent = `${tokens.length ? "找到" : "共"} ${visibleDocuments} 份资料`;
  noResults.hidden = visibleDocuments > 0;
}

if (levels.length) {
  search.addEventListener("input", filterCatalog);
  window.addEventListener("pageshow", filterCatalog);
}
