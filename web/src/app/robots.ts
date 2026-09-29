/**
 * robots.ts – Next.js App Router Generative Route-Config.
 *
 * Verbietet alle Suchmaschinen-Crawling für die gesamte App.
 * Wird als text/plain ausgegeben (wie klassische robots.txt).
 */

export default function robots() {
  return {
    rules: [
      {
        userAgent: "*",
        disallow: "/",
      },
    ],
    // Sitemap ist nicht gesetzt / interner Betrieb.
    // Wenn eine URL hinzukommt, hier einfügen oder auskommentieren:
    // sitemapURL: "https://example.com/sitemap.xml",
  };
}
