"""Wildberries parser."""

import asyncio
import logging
import re
from pathlib import Path
from uuid import uuid4

import pandas as pd
from playwright.async_api import async_playwright, expect, Page
from tqdm import tqdm

from settings import BROWSER_ARGS, CONTEXT_KWARGS, INIT_SCRIPT

MAIN_URL = "https://www.wildberries.ru/catalog/0/search.aspx?search=пальто%20из%20натуральной%20шерсти"  # noqa: E501

ERRORS_DIR = Path("errors")
ERRORS_DIR.mkdir(exist_ok=True)

BAD_SYMBOLS_RE = re.compile(r"[<>:\"/\\\|\?\*#%&{}$!@+'`=]+")
NON_DIGIT_RE = re.compile(r"\D+")
SPACE_RE = re.compile(r"\s+")


async def save_error_page(page: Page) -> None:
    """
    Utility function to save a page
    (screenshot and full page HTML for debugging purposes).

    Args:
        page: a Playwright Page object
    """
    filename = (
        f"{SPACE_RE.sub('_', BAD_SYMBOLS_RE.sub('', await page.title()))}"
        f"{uuid4()}"
    )[:214]

    await page.screenshot(path=ERRORS_DIR / f"{filename}.png")

    with (ERRORS_DIR / f"{filename}.html").open("w") as file:
        file.write(await page.content())


async def get_images_links(page) -> str:
    """
    Get images links from the product page.

    Args:
        page: a Playwright Page object

    Returns:
        A string with images links separated by comma
    """
    links = []

    while await (
        image_locator := page.locator("div.imgContainer--N9WXW img")
    ).count():
        link = await image_locator.get_attribute("src")
        if link in links:
            break
        links.append(link)
        await page.locator(
            "button.navigationButton--m4UOz.mainSliderNavigationButton--Ny6xH.right--NVWsK"  # noqa: E501
        ).click()
        await page.wait_for_timeout(1000)

    return ",".join(links)


async def get_desc_and_other_params(page) -> dict:
    """
    Get description and other product parameters from the product page.

    Args:
        page: a Playwright Page object

    Returns:
        A dict with product parameters
    """
    result = {}
    await page.locator("span:has-text('Характеристики и описание')").click()
    await page.wait_for_timeout(1000)

    result["Описание"] = await page.locator(
        "p.descriptionText--Jq9n2"
    ).inner_text()

    rows = await page.locator("table.table--tSF0X.table--CGApj tr'").all()

    for row in rows:
        key = await row.locator("th.cellKey--eGe6N").inner_text()
        value = await row.locator("td.cellValue--hHBJB").inner_text()
        result[key] = value

    return result


async def parse_product(url: str) -> dict:
    """
    Parse product info from the product page.

    Args:
        url: an URL of the product page

    Returns:
        dict with product info
    """
    result = {"Ссылка": url}

    async with async_playwright() as p:
        browser = await p.chromium.launch(args=BROWSER_ARGS)
        context = await browser.new_context(**CONTEXT_KWARGS)
        await context.add_init_script(INIT_SCRIPT)
        try:
            page = await browser.new_page()
            await page.goto(url, wait_until="networkidle")
            result["Артикул"] = await page.locator(
                "td.cellValue--hHBJB.cellCopyContainer--RPw81"
            ).inner_text()
            result["Название"] = await page.locator(
                "h3.productTitle--J2W7I"
            ).inner_text()
            result["Цена"] = int(
                NON_DIGIT_RE.sub(
                    await page.locator("ins.priceBlockFinalPrice--iToZR"), ""
                )
            )
            seller_locator = page.locator("a.productHeaderBrand--UlsTx")
            result["Название селлера"] = await seller_locator.inner_text()
            result["Ссылка на селлера"] = (
                "https://www.wildberries.ru"
                f"{await seller_locator.get_attribute('href')}"
            )
            rating_locator_text = await page.locator(
                "span.productReviewRating--gQDQG"
            ).inner_text()
            result["Рейтинг"] = float(
                rating_locator_text.split(" ")[0].replace(",", ".")
            )
            result["Количество отзывов"] = int(
                rating_locator_text.split(" ")[2]
            )
            result["Размеры"] = await page.evaluate(
                """() => {
                const elements = document.querySelectorAll('span.sizesListSize--NUoNC');
                return Array.from(elements).map(el => el.innerText).join(', ');
                }"""
            )
            result["Изображения"] = await get_images_links(page)
            result += await get_desc_and_other_params(page)
            logging.info(f"Scraped product info: {result}")
        except Exception:
            logging.exception("Error while parsing product page")
            await save_error_page(page)
            result = {}
        finally:
            await browser.close()

    return result


async def get_products_urls(main_url: str) -> list[str]:
    """
    Parse product urls from the main page.

    Args:
        main_url: a URL of the main page with products

    Returns:
        A list of product URLs
    """
    urls = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(args=BROWSER_ARGS)
        context = await browser.new_context(**CONTEXT_KWARGS)
        await context.add_init_script(INIT_SCRIPT)
        try:
            page = await browser.new_page()
            await page.goto(main_url, wait_until="networkidle")
            await expect(page.locator(".product-card__link")).to_be_visible()
            previous_count = 0
            while True:
                logging.info("Scrolling...")
                await page.evaluate(
                    "window.scrollTo(0, document.body.scrollHeight)"
                )
                await page.wait_for_timeout(2000)
                current_count = await page.locator(
                    ".product-card__link"
                ).count()
                if current_count == previous_count:
                    break
                previous_count = current_count
            urls = await page.locator(".product-card__link").evaluate_all(
                "elements => elements.map(el => el.href)"
            )
        except Exception:
            logging.exception("Error while parsing product urls")
            await save_error_page(page)
        finally:
            await browser.close()
        if not urls:
            logging.warning("No products were parsed")
            await save_error_page(page)

    return urls


async def main():
    """Parse wildberries.ru site and save results to Excel file."""
    urls = await get_products_urls(MAIN_URL)
    logging.info(f"{len(urls)} products were found")

    if urls:
        result_df = pd.DataFrame(
            result
            for result in [
                await parse_product(url)
                for url in tqdm(urls, desc="Parsing product pages...")
            ]
            if result
        )
        result_df_filtered = result_df[
            (result_df["Рейтинг"] >= 4.5)
            & (result_df["Цена"] <= 10000)
            & (result_df["Страна производства"] == "Россия")
        ]
        result_df.to_excel("result.xlsx", index=False)
        result_df_filtered.to_excel("result_filtered.xlsx", index=False)


if __name__ == "__main__":
    asyncio.run(main())
