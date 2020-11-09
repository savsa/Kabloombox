import os
import logging

from kabloombox import app, views, api

if __name__ == "__main__":
    if os.getenv("GAE_ENV", "").startswith("standard"):
        app.run()  # production
    else:
        logging.debug(
            "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        )
        logging.critical(
            "Credendtials from environ: {}".format(
                os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
            )
        )
        app.run(port=8080, host="localhost", debug=True)  # localhost
