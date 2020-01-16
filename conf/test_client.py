from datetime import datetime

from django.test import testcases

from conf import colours, settings


class LiteHMRCTestClient(testcases.TestCase):
    @classmethod
    def tearDownClass(cls):
        pass

    def setUp(self):
        if settings.TIME_TESTS:
            self.tick = datetime.now()

    def tearDown(self):
        """
        Print output time for tests if settings.TIME_TESTS is set to True
        """
        if settings.TIME_TESTS:
            self.tock = datetime.now()

            diff = self.tock - self.tick
            time = round(diff.microseconds / 1000, 2)
            colour = colours.green
            emoji = ""

            if time > 100:
                colour = colours.orange
            if time > 300:
                colour = colours.red
                emoji = " 🔥"

            print(self._testMethodName + emoji + " " + colour(str(time) + "ms") + emoji)
