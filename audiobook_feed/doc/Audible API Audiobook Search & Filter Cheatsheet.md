# 📚 **Audible API: Audiobook Search & Filter Cheatsheet**

## **1. API Endpoint**

```bash
https://api.audible.com/1.0/catalog/products
```

### **Core Query Parameters**

* `title` – Search term (book, series, or keyword)
* `num_results` – Max results per page (`1-50`)
* `products_sort_by` – Sorting (`-ReleaseDate` for newest first)
* `page` – For pagination (start with 1, increment as needed)
* `response_groups` – Include extra fields: `product_desc,media,contributors,series` (and more if needed)

---

## **2. Relevant Keys to Extract**

| Key                     | Description                                         | Notes                          |
| ----------------------- | --------------------------------------------------- | ------------------------------ |
| `title`                 | Book Title                                          | String                         |
| `authors`               | List of authors, use `[0].name`                     | Fallback to `"N/A"` if missing |
| `series`                | Array, use `[0].title` for series name              | Fallback to `"N/A"` if missing |
| `series_number`         | `[0].sequence` from `series`                        | Fallback to `"N/A"`            |
| `release_date`          | Publication/release date                            | String, `"YYYY-MM-DD"`         |
| `narrators`             | List of narrators, use `[0].name`                   | Fallback to `"N/A"`            |
| `asin`                  | Audible's unique ID for the product                 | Always present                 |
| `link`                  | Construct as `"https://www.audible.com/pd/" + asin` |                                |
| `content_type`          | Used for filtering ("Podcast" for podcasts)         | See below                      |
| `content_delivery_type` | Extra podcast filtering if needed                   | "PodcastEpisode" means podcast |

*You can add more fields if desired, like `publisher_name`, `runtime_length_min`, `product_images`, etc.*

---

## **3. Filter Out:**

* **Podcasts:**
  `content_type == "Podcast"` (case-insensitive)
* **Podcast Episodes:**
  If you ever see `"Podcast"` in `content_delivery_type`, filter out with:

  ```jq
  select(
    ((.content_type // "" | ascii_downcase) != "podcast")
    and
    ((.content_delivery_type // "" | ascii_downcase | contains("podcast") | not))
  )
  ```
* **Other filters (optional):**

  * Exclude non-English (`language`)
  * Exclude summaries/drama CDs by checking for weird patterns in title/author/publisher

---

## **4. Paging and API Limitations**

* **Audible API only returns 50 results per request** (`num_results=50`)
* Use `page` parameter to fetch additional results
* Loop pages until you get fewer than 50 results back

---

## **5. Example: Bash One-Liner**

```bash
curl 'https://api.audible.com/1.0/catalog/products?title=Mushoku%20Tensei&num_results=50&products_sort_by=-ReleaseDate&response_groups=product_desc,media,contributors,series' \
| jq '.products[]
    | select(((.content_type // "" | ascii_downcase) != "podcast")
      and ((.content_delivery_type // "" | ascii_downcase | contains("podcast") | not)))
    | {
        title: .title,
        author: (.authors[0].name // "N/A"),
        series: (.series[0].title // "N/A"),
        series_number: (.series[0].sequence // "N/A"),
        release: .release_date,
        narrator: (.narrators[0].name // "N/A"),
        asin: .asin,
        link: ("https://www.audible.com/pd/" + (.asin // ""))
      }'
```

---

## **6. Paging Example (Bash Loop for up to 200 Results):**

```bash
for page in {1..4}; do
  curl -s "https://api.audible.com/1.0/catalog/products?title=Mushoku%20Tensei&num_results=50&page=$page&products_sort_by=-ReleaseDate&response_groups=product_desc,media,contributors,series" \
  | jq '.products[]
      | select(((.content_type // "" | ascii_downcase) != "podcast")
        and ((.content_delivery_type // "" | ascii_downcase | contains("podcast") | not)))
      | {
          title: .title,
          author: (.authors[0].name // "N/A"),
          series: (.series[0].title // "N/A"),
          series_number: (.series[0].sequence // "N/A"),
          release: .release_date,
          narrator: (.narrators[0].name // "N/A"),
          asin: .asin,
          link: ("https://www.audible.com/pd/" + (.asin // ""))
        }'
done
```

---

## **7. Gotchas & Notes**

* **Case Sensitivity:** Always use `ascii_downcase` for string checks.
* **Missing Data:** Use `// "N/A"` for safe defaults.
* **Duplicate Titles:** Sometimes you’ll get multiple entries per book—filter/merge if you want only the latest.
* **Rate Limits:** The public API can start throttling if you’re aggressive. If so, add a `sleep 1` in your loop.

---

## **Summary Table**

| Extract Field     | Audible JSON Key Path                       | Filtering? |
| ----------------- | ------------------------------------------- | ---------- |
| Title             | `.title`                                    |            |
| Author            | `.authors[0].name`                          |            |
| Series            | `.series[0].title`                          |            |
| Series #          | `.series[0].sequence`                       |            |
| Release Date      | `.release_date`                             |            |
| Narrator          | `.narrators[0].name`                        |            |
| ASIN              | `.asin`                                     |            |
| Link              | `"https://www.audible.com/pd/" + .asin`     |            |
| Exclude Podcast   | `.content_type == "Podcast"`                | Yes        |
| Exclude PodcastEp | `.content_delivery_type` contains "Podcast" | Yes        |

---

## **Level-Up Ideas**

* **Output as CSV, JSON, or Markdown for import to other tools**
* **Compare ASINs to your local collection to find what you’re missing**
* **Automate “new release” notifications with a cron job + Discord/Gotify/Push**

---


