import logging
import threading

logger = logging.getLogger(__name__)

class MetaSingleton(type):
    __instances = {}  # noqa: RUF012

    def __call__(cls, *args, **kwargs):
        if cls not in cls.__instances:
            if isinstance(threading.current_thread(), threading._DummyThread):
                logger.warning(
                    f"{cls.__name__}, which is a singleton class, is initialized from a thread "
                    "not started by Python itself. It is not safe and should be avoided. If you "
                    "encounter any errors please consider initializing this class beforehand in "
                    "the main Python thread."
                )
            cls.__instances[cls] = super().__call__(*args, **kwargs)

        return cls.__instances[cls]
