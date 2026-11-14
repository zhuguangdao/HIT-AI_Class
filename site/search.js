const search = document.querySelector("#search");
const courses = [...document.querySelectorAll(".course")].map((section) => ({
  section,
  title: section.querySelector("h3").textContent.toLocaleLowerCase(),
  navigation: document.querySelector(`.category-list a[href="#${section.id}"]`),
  count: section.querySelector(".course-count"),
  documents: [...section.querySelectorAll(".document")].map((row) => ({
    row,
    title: row.querySelector(".document-title").textContent.toLocaleLowerCase(),
  })),
}));
const resultsCount = document.querySelector("#results-count");
const noResults = document.querySelector("#no-results");

function filterCatalog() {
  const tokens = search.value.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
  let visibleDocuments = 0;

  for (const course of courses) {
    let courseCount = 0;
    for (const document of course.documents) {
      const searchableText = `${course.title} ${document.title}`;
      const matches = tokens.every((token) => searchableText.includes(token));
      document.row.hidden = !matches;
      courseCount += Number(matches);
    }
    course.section.hidden = courseCount === 0;
    course.navigation.parentElement.hidden = courseCount === 0;
    course.navigation.querySelector("small").textContent = courseCount;
    course.count.textContent = `${courseCount} 份`;
    visibleDocuments += courseCount;
  }

  resultsCount.textContent = tokens.length
    ? `找到 ${visibleDocuments} 份 PDF`
    : `共 ${visibleDocuments} 份 PDF`;
  noResults.hidden = visibleDocuments > 0;
}

if (courses.length) {
  search.addEventListener("input", filterCatalog);
  window.addEventListener("pageshow", filterCatalog);
}
