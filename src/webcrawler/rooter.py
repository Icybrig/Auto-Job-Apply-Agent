from crawlee.router import Router
from crawlee.crawlers import PlaywrightCrawlingContext, BeautifulSoupCrawlingContext
from typing import Union

router = Router[Union[PlaywrightCrawlingContext, BeautifulSoupCrawlingContext]]()


@router.default_handler
def default_handler(context: PlaywrightCrawlingContext):
    context.log.info("Defualt")
