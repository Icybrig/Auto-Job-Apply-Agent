from crawlee.router import Router
from crawlee.crawlers import PlaywrightCrawlingContext

router = Router[PlaywrightCrawlingContext]()


@router.default_handler
def default_handler(context: PlaywrightCrawlingContext):
    context.log.info("Defualt")
