from joblib import Parallel, delayed
from random import sample
from .webpage2html import short_cut


def get_urls(urls):
    """
    並列処理

    Args:
        urls:

    Returns:

    """

    def _process(url):
        return short_cut(url)

    target_urls = sample(urls, len(urls))
    r = Parallel(n_jobs=-1)([delayed(_process)(url) for url in target_urls])
