import truststore
truststore.inject_into_ssl()

from tabulate import tabulate

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import pandas as pd
rows = []

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(user_agent="Mozilla/5.0")
    page.goto(r"https://www.linkedin.com/jobs/search?keywords=python&location=United%20States&geoId=103644278&trk=public_jobs_jobs-search-bar_search-submit&original_referer=https%3A%2F%2Fwww.linkedin.com%2Fjobs%2Fsearch%3Flipi%3Durn%253Ali%253Apage%253Ad_homepage-guest-home_jsbeacon%253BkQd68csVSFSXHyRU48FgNA%253D%253D%26position%3D1%26pageNum%3D0&position=1&pageNum=0")

    while len(rows) < 50:
        # DIAGNOSTIC: if LinkedIn serves a bad page, say so instead of crashing
        try:
            page.wait_for_selector("div.base-search-card", state="attached", timeout=20000)
        except Exception:
            print("No cards. Title:", page.title(), "| URL:", page.url)
            page.screenshot(path="debug_linkedin.png", full_page=True)
            browser.close()
            raise SystemExit

        page.wait_for_timeout(2000)
        html_text = page.content()

        # DIAGNOSTIC: save the page so you can debug offline
        with open("linkedin_page.html", "w", encoding="utf-8") as f:
            f.write(html_text)

        soup = BeautifulSoup(html_text, "lxml")

        jobs = soup.find_all('div', class_ = "base-search-card")
        print("Cards found:", len(jobs))

        # DIAGNOSTIC: which selector matches nothing?
        checks = {
            "title":    ("h3",   "base-search-card__title"),
            "company":  ("h4",   "base-search-card__subtitle"),
            "posted":   ("span", "job-search-card__listdate"),
            "location": ("span", "job-search-card__location"),
        }
        for name, (tag, cls) in checks.items():
            found = sum(1 for j in jobs if j.find(tag, class_=cls))
            print(f"{name}: {found}/{len(jobs)}")
        print("link:", sum(1 for j in jobs if j.find("a")), "/", len(jobs))

        # DIAGNOSTIC: show the real HTML of the first card
        if jobs:
            print(jobs[0].prettify()[:2500])

        for job in jobs:
            try:
                job_name = job.find("h3", class_ = "base-search-card__title").get_text(strip=True)
                job_company_name = job.find("h4", class_ = "base-search-card__subtitle").get_text(strip=True)
                job_posted_on = job.find("time").get_text(strip=True)
                place_of_job = job.find("span", class_ = "job-search-card__location").get_text(strip=True)
                job_link = job.find("a")["href"]
                if (job_name, job_company_name, job_posted_on, place_of_job, job_link) not in rows:
                    rows.append((job_name,job_company_name, job_posted_on, place_of_job, job_link))
            except AttributeError as e:  # DIAGNOSTIC: print the error instead of hiding it
                print("Skipped:", e)
                continue

        next_button = page.locator("button.pagination-next")
        if next_button.count() == 0 or next_button.first.is_disabled():
            break
        next_button.first.click()
        page.wait_for_timeout(3000)

    browser.close()

print(tabulate(rows[:50], headers=["Job Designation", "Company", "Job posted ", "Place of job", "job_link"], tablefmt="grid"))

df = pd.DataFrame(rows[:50], columns = ["Job Designation", "Company", "Job Posted on", "Place of job", "job_link"])
df.to_csv("jobs_on_linkedin.csv", index=False, encoding="utf-8-sig")