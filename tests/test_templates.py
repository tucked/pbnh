import pytest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
from webdriver_manager.firefox import GeckoDriverManager


@pytest.fixture(
    params=[
        pytest.param(
            (
                webdriver.Chrome,
                ChromeService(
                    ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()
                ),
                webdriver.ChromeOptions(),
            ),
            id="Chromium",
        ),
        pytest.param(
            (
                webdriver.Firefox,
                FirefoxService(GeckoDriverManager().install()),
                webdriver.FirefoxOptions(),
            ),
            id="Firefox",
        ),
    ],
)
def browser(request):
    """Get a browser to test the Web UI with."""
    driver, service, options = request.param
    options.add_argument("--headless")
    if driver is webdriver.Chrome:
        options.binary_location = "/usr/bin/chromium"
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
    with driver(service=service, options=options) as browser:
        yield browser


@pytest.fixture
def example_paste(server_url):
    """Get the content and response JSON of an existing paste."""
    hashid = "f8b6435a007d84cb7276371ad1e091ad317512d5"
    return b"Example Paste", {
        "hashid": hashid,
        "link": f"{server_url}/{hashid}",
    }


def test_save_existing(browser, server_url, example_paste):
    """Creating a paste in the Web UI should redirect to the link in the response."""
    content, response_json = example_paste
    browser.get(server_url)
    WebDriverWait(browser, 5).until(
        lambda driver: driver.execute_script("return !!window.editor")
    )
    browser.execute_script("window.editor.setValue(arguments[0]);", content.decode())
    browser.find_element(By.ID, "save").click()
    expected = response_json["link"] + "/text"
    WebDriverWait(browser, 5).until(EC.url_to_be(expected))
    assert browser.current_url == expected
