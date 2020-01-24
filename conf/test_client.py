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

        self.file_name = "ILBDOTI_live_CHIEF_usageData_9876_201901130300"
        self.file_body = """1\\fileHeader\\CHIEF\\SPIRE\\usageData\\201901130300\\9876\\
                        2\\licenceUsage\\LU04148/00001\\insert\\GBOIE2017/12345B\\O\\
                        3\\line\\1\\0\\0\\
                        4\\usage\\O\\9GB000001328000-PE112345\\R\\20190112\\0\\0\\\\000262\\\\\\\\
                        5\\usage\\O\\9GB000001328000-PE112345\\L\\20190112\\0\\0\\\\000262\\\\\\\\
                        6\\usage\\O\\9GB000001328000-PE112345\\K\\20190112\\0\\0\\\\000262\\\\\\\\
                        7\\end\\line\\5
                        8\\end\\licenceUsage\\7
                        9\\licenceUsage\\LU04148/00002\\insert\\GBOGE2014/23456\\O\\
                        10\\line\\1\\0\\0\\
                        11\\usage\\O\\9GB000003133000-445251012345\\Z\\20190112\\0\\0\\\\000962\\\\\\\\
                        12\\end\\line\\3
                        13\\end\\licenceUsage\\5
                        14\\licenceUsage\\LU04148/00003\\insert\\GBOGE2018/34567\\O\\
                        15\\line\\1\\0\\0\\
                        16\\usage\\O\\9GB000001328000-PE112345\\A\\20190112\\0\\0\\\\000442\\\\\\\\
                        17\\end\\line\\3
                        18\\end\\licenceUsage\\5
                        19\\licenceUsage\\LU04148/00004\\insert\\GBSIE2018/45678\\O\\
                        20\\line\\1\\3\\0\\
                        21\\usage\\O\\9GB00000133000-774170812345\\D\\20190112\\3\\0\\\\009606\\\\\\\\
                        22\\end\\line\\3
                        23\\end\\licenceUsage\\5
                        24\\licenceUsage\\LU04148/00005\\insert\\GBOGE2011/56789\\O\\
                        25\\line\\1\\0\\0\\
                        26\\usage\\O\\9GB000004988000-4750437112345\\G\\20190111\\0\\0\\\\000104\\\\\\\\
                        27\\usage\\O\\9GB000004988000-4750436912345\\Y\\20190111\\0\\0\\\\000104\\\\\\\\
                        28\\end\\line\\4
                        29\\end\\licenceUsage\\6
                        30\\licenceUsage\\LU04148/00006\\insert\\GBOGE2017/98765\\O\\
                        31\\line\\1\\0\\0\\
                        32\\usage\\O\\9GB000002816000-273993\\L\\20190109\\0\\0\\\\000316\\\\\\\\
                        33\\end\\line\\3
                        34\\end\\licenceUsage\\5
                        35\\licenceUsage\\LU04148/00007\\insert\\GBOGE2015/87654\\O\\
                        36\\line\\1\\0\\0\\
                        37\\usage\\O\\9GB000003133000-784920212345\\E\\20190111\\0\\0\\\\000640\\\\\\\\
                        38\\usage\\O\\9GB000003133000-784918012345\\D\\20190111\\0\\0\\\\000640\\\\\\\\
                        39\\end\\line\\4
                        40\\end\\licenceUsage\\6
                        41\\fileTrailer\\7""".encode(
            "ascii", "replace"
        )

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
