import unittest
from pyOKR_VOs_CPUs_Accounting.services.accounting_service import AccountingService as AS

class TestAccountingService(unittest.TestCase):
    def setUp(self):
        self.env = {
            'ACCOUNTING_SCOPE': 'cloud',
            'LOG': 'DEBUG'
        }
        self.service = AS(self.env)

    def test_process_accounting_data(self):
        data = [
            {"2024-10": 5952, "2024-11": 5759.9978, "2024-12": 5952, "id": "ALICE", "Total": 17664, "Percent": 0.12},
            {"2024-10": 49848, "2024-11": 48240.0187, "2024-12": 49847.9813, "id": "aquamonitor.c-scale.eu", "Total": 147936, "Percent": 0.97},
            {"2024-10": 3955.6669, "2024-11": 1170.8039, "2024-12": 1097.8353, "id": "belle", "Total": 6224, "Percent": 0.04},
            {"2024-10": 19344, "2024-11": 18720.0072, "2024-12": 19343.9928, "id": "bioisi", "Total": 57408, "Percent": 0.37},
            {"2024-10": 62535.0589, "2024-11": 60762.2429, "2024-12": 60195.3655, "id": "biomed", "Total": 183493, "Percent": 1.2},
            {"2024-10": 1490.0006, "2024-11": 1439.9994, "2024-12": 1488, "id": "cesga.es", "Total": 4418, "Percent": 0.03},
            {"2024-10": 16381.9967, "2024-11": 15840.0272, "2024-12": 16368.0434, "id": "cloud.egi.eu", "Total": 48590, "Percent": 0.32},
            {"2024-10": 68263.0493, "2024-11": 61944.074, "2024-12": 68352, "id": "deep-hybrid-datacloud.eu", "Total": 198559, "Percent": 1.3},
            {"2024-10": 745, "2024-11": 720, "2024-12": 669.757, "id": "demo.fedcloud.egi.eu", "Total": 2135, "Percent": 0.01},
            {"2024-10": 27070.2896, "2024-11": 28105.9886, "2024-12": 23808, "id": "dev.intertwin.eu", "Total": 78984, "Percent": 0.52},
            {"2024-10": 2980, "2024-11": 2880, "2024-12": 2976, "id": "dteam", "Total": 8836, "Percent": 0.06},
            {"2024-10": 16965.7967, "2024-11": 17280, "2024-12": 16704, "id": "eiscat.se", "Total": 50950, "Percent": 0.33},
            {"2024-10": 93183.9977, "2024-11": 81250.2267, "2024-12": 72912.0205, "id": "eli-np.eu", "Total": 247346, "Percent": 1.62},
            {"2024-10": 3969.3789, "2024-11": 5683.2167, "2024-12": 14175.5811, "id": "enmr.eu", "Total": 23828, "Percent": 0.16},
            {"2024-10": 40967.026, "2024-11": 39600.1329, "2024-12": 40920.2328, "id": "eosc-synergy.eu", "Total": 121487, "Percent": 0.79},
            {"2024-10": 5960, "2024-11": 5760, "2024-12": 4979.9533, "id": "eval.c-scale.eu", "Total": 16700, "Percent": 0.11},
            {"2024-10": 2249.4208, "2024-11": 2175.0837, "2024-12": 2249.7022, "id": "fedcloud.egi.eu", "Total": 6674, "Percent": 0.04},
            {"2024-10": 32736, "2024-11": 31680, "2024-12": 32736.0122, "id": "gridifin.ro", "Total": 97152, "Percent": 0.63},
            {"2024-10": 47680, "2024-11": 46080, "2024-12": 47616, "id": "icecube", "Total": 141376, "Percent": 0.92},
            {"2024-10": 120527.9589, "2024-11": 116640.0428, "2024-12": 120527.955, "id": "lagoproject.net", "Total": 357696, "Percent": 2.34},
            {"2024-10": 8192.4616, "2024-11": 7378.2394, "2024-12": 8184.055, "id": "mswss.ui.savba.sk", "Total": 23755, "Percent": 0.16},
            {"2024-10": 4470.0033, "2024-11": 4320.0167, "2024-12": 4464.03, "id": "mteam.data.kit.edu", "Total": 13254, "Percent": 0.09},
            {"2024-10": 112980.0333, "2024-11": 106560.075, "2024-12": 113039.975, "id": "opencoast.eosc-hub.eu", "Total": 332580, "Percent": 2.17},
            {"2024-10": 13956.9434, "2024-11": 0, "2024-12": 0, "id": "openrisknet.org", "Total": 13957, "Percent": 0.09},
            {"2024-10": 38224.4753, "2024-11": 24140.8327, "2024-12": 20939.4548, "id": "ops", "Total": 83305, "Percent": 0.54},
            {"2024-10": 43210, "2024-11": 41760, "2024-12": 43152, "id": "peachnote.com", "Total": 128122, "Percent": 0.84},
            {"2024-10": 299005.6728, "2024-11": 214560, "2024-12": 126927, "id": "perla-pv.ro", "Total": 640493, "Percent": 4.18},
            {"2024-10": 11904, "2024-11": 11520.0039, "2024-12": 11903.9956, "id": "saps-vo.i3m.upv.es", "Total": 35328, "Percent": 0.23},
            {"2024-10": 110935.145, "2024-11": 36205.7154, "2024-12": 7559.4555, "id": "training.egi.eu", "Total": 154700, "Percent": 1.01},
            {"2024-10": 47680, "2024-11": 46080, "2024-12": 47616, "id": "umsa.cerit-sc.cz", "Total": 141376, "Percent": 0.92},
            {"2024-10": 238522.9108, "2024-11": 179025.1378, "2024-12": 107880, "id": "virgo", "Total": 525428, "Percent": 3.43},
            {"2024-10": 137343.782, "2024-11": 135624.2605, "2024-12": 114030.3714, "id": "vo.access.egi.eu", "Total": 386998, "Percent": 2.53},
            {"2024-10": 1231119.6874, "2024-11": 1128575.9676, "2024-12": 1226795.4423, "id": "vo.ai4eosc.eu", "Total": 3586491, "Percent": 23.42},
            {"2024-10": 8319.9889, "2024-11": 0, "2024-12": 0, "id": "vo.ai4publicpolicy.eu", "Total": 8320, "Percent": 0.05},
            {"2024-10": 56164.1867, "2024-11": 57243.6956, "2024-12": 56895.2878, "id": "vo.aneris.eu", "Total": 170303, "Percent": 1.11},
            {"2024-10": 40230, "2024-11": 38880, "2024-12": 40176, "id": "vo.clarin.eu", "Total": 119286, "Percent": 0.78},
            {"2024-10": 11904, "2024-11": 11519.9956, "2024-12": 11904.0044, "id": "vo.complex-systems.eu", "Total": 35328, "Percent": 0.23},
            {"2024-10": 20859.9922, "2024-11": 20160.0078, "2024-12": 20831.9922, "id": "vo.decido-project.eu", "Total": 61852, "Percent": 0.4},
            {"2024-10": 146020.0544, "2024-11": 141119.9456, "2024-12": 145824, "id": "vo.deltares.nl", "Total": 432964, "Percent": 2.83},
            {"2024-10": 744.9997, "2024-11": 720, "2024-12": 464.0003, "id": "vo.ebrain-health.eu", "Total": 1929, "Percent": 0.01},
            {"2024-10": 25330, "2024-11": 24480, "2024-12": 25296, "id": "vo.emphasisproject.eu", "Total": 75106, "Percent": 0.49},
            {"2024-10": 744.9997, "2024-11": 720.0003, "2024-12": 743.9997, "id": "vo.emso-eric.eu", "Total": 2209, "Percent": 0.01},
            {"2024-10": 71242.3467, "2024-11": 67680, "2024-12": 87177.8601, "id": "vo.enes.org", "Total": 226100, "Percent": 1.48},
            {"2024-10": 5960, "2024-11": 5760, "2024-12": 5952, "id": "vo.envrihub.eu", "Total": 17672, "Percent": 0.12},
            {"2024-10": 11175, "2024-11": 10800, "2024-12": 11160, "id": "vo.eoscfuture-sp.panosc.eu", "Total": 33135, "Percent": 0.22},
            {"2024-10": 4464, "2024-11": 4320.0017, "2024-12": 4463.9983, "id": "vo.europlanet-vespa.eu", "Total": 13248, "Percent": 0.09},
            {"2024-10": 6610, "2024-11": 7980, "2024-12": 4680.0028, "id": "vo.eurosea.marine.ie", "Total": 19270, "Percent": 0.13},
            {"2024-10": 101184.7046, "2024-11": 95472.0282, "2024-12": 82937.0275, "id": "vo.france-grilles.fr", "Total": 279594, "Percent": 1.83},
            {"2024-10": 35760, "2024-11": 34560, "2024-12": 35712, "id": "vo.geoss.eu", "Total": 106032, "Percent": 0.69},
            {"2024-10": 225842.6844, "2024-11": 220320.046, "2024-12": 227663.9152, "id": "vo.grand-est.fr", "Total": 673827, "Percent": 4.4},
            {"2024-10": 640541.675, "2024-11": 615828.4421, "2024-12": 643111.687, "id": "vo.imagine-ai.eu", "Total": 1899482, "Percent": 12.4},
            {"2024-10": 12648, "2024-11": 12240.0014, "2024-12": 12647.9953, "id": "vo.instruct.eu", "Total": 37536, "Percent": 0.25},
            {"2024-10": 7670.0056, "2024-11": 6960.0083, "2024-12": 2459.9917, "id": "vo.latitudo40.com.eu", "Total": 17090, "Percent": 0.11},
            {"2024-10": 71424, "2024-11": 69120.0144, "2024-12": 71423.9734, "id": "vo.lethe-project.eu", "Total": 211968, "Percent": 1.38},
            {"2024-10": 87792, "2024-11": 84960.0328, "2024-12": 87791.9672, "id": "vo.lifewatch.eu", "Total": 260544, "Percent": 1.7},
            {"2024-10": 123531.9922, "2024-11": 119520.01, "2024-12": 123503.9811, "id": "vo.nbis.se", "Total": 366556, "Percent": 2.39},
            {"2024-10": 128885, "2024-11": 124560, "2024-12": 128712, "id": "vo.nextgeoss.eu", "Total": 382157, "Percent": 2.5},
            {"2024-10": 51405, "2024-11": 49680, "2024-12": 51336, "id": "vo.notebooks.egi.eu", "Total": 152421, "Percent": 1},
            {"2024-10": 29146.0209, "2024-11": 26448.0317, "2024-12": 29184, "id": "vo.obsea.es", "Total": 84778, "Percent": 0.55},
            {"2024-10": 12267.2533, "2024-11": 11520.0444, "2024-12": 10330.8245, "id": "vo.oipub.com", "Total": 34118, "Percent": 0.22},
            {"2024-10": 29874.8133, "2024-11": 28800.0017, "2024-12": 29759.9888, "id": "vo.operas-eu.org", "Total": 88435, "Percent": 0.58},
            {"2024-10": 166880, "2024-11": 159908.84, "2024-12": 154752, "id": "vo.pangeo.eu", "Total": 481541, "Percent": 3.14},
            {"2024-10": 65472, "2024-11": 63360, "2024-12": 65472.0244, "id": "vo.qc-md.eli-np.eu", "Total": 194304, "Percent": 1.27},
            {"2024-10": 152583.7404, "2024-11": 135901.6995, "2024-12": 139871.9477, "id": "vo.sbg.in2p3.fr", "Total": 428357, "Percent": 2.8},
            {"2024-10": 2980, "2024-11": 2880, "2024-12": 2976, "id": "vo.thepund.it", "Total": 8836, "Percent": 0.06},
            {"2024-10": 132562.0055, "2024-11": 128160.1611, "2024-12": 132432.2278, "id": "vo.usegalaxy.eu", "Total": 393154, "Percent": 2.57},
            {"2024-10": 38688, "2024-11": 37440.0143, "2024-12": 38687.9857, "id": "worsica.vo.incd.pt", "Total": 114816, "Percent": 0.75},
            {"2024-10": 5447258, "2024-11": 4946505, "2024-12": 4921749, "id": "Total", "Total": 15315512, "Percent": ""},
            {"2024-10": "35.57%", "2024-11": "32.30%", "2024-12": "32.14%", "id": "Percent", "Percent": "", "Total": ""},
            {"id":"xlegend", "0": "ALICE", "1": "aquamonitor.c-scale.eu", "2": "belle", "3": "bioisi", "4": "biomed", "5": "cesga.es", "6": "cloud.egi.eu", "7": "deep-hybrid-datacloud.eu", "8": "demo.fedcloud.egi.eu", "9": "dev.intertwin.eu", "10": "dteam", "11": "eiscat.se", "12": "eli-np.eu", "13": "enmr.eu", "14": "eosc-synergy.eu", "15": "eval.c-scale.eu", "16": "fedcloud.egi.eu", "17": "gridifin.ro", "18": "icecube", "19": "lagoproject.net", "20": "mswss.ui.savba.sk", "21": "mteam.data.kit.edu", "22": "opencoast.eosc-hub.eu", "23": "openrisknet.org", "24": "ops", "25": "peachnote.com", "26": "perla-pv.ro", "27": "saps-vo.i3m.upv.es", "28": "training.egi.eu", "29": "umsa.cerit-sc.cz", "30": "virgo", "31": "vo.access.egi.eu", "32": "vo.ai4eosc.eu", "33": "vo.ai4publicpolicy.eu", "34": "vo.aneris.eu", "35": "vo.clarin.eu", "36": "vo.complex-systems.eu", "37": "vo.decido-project.eu", "38": "vo.deltares.nl", "39": "vo.ebrain-health.eu", "40": "vo.emphasisproject.eu", "41": "vo.emso-eric.eu", "42": "vo.enes.org", "43": "vo.envrihub.eu", "44": "vo.eoscfuture-sp.panosc.eu", "45": "vo.europlanet-vespa.eu", "46": "vo.eurosea.marine.ie", "47": "vo.france-grilles.fr", "48": "vo.geoss.eu"},
            {"id": "ylegend", "0": "2024-10", "1": "2024-11", "2": "2024-12", "3": "id"},
            {"id": "var", "xrange": "DATE", "yrange": "VO", "query": "sum_elap_processors"}
            ]
        
        summary = self.service.process_accounting_data(data)

        expected_total = len([item for item in data if "id" in item and item["id"] not in ["Total", "Percent", "xlegend", "ylegend", "var"]])
        self.assertEqual(summary["total"], expected_total)
        self.assertEqual(summary["total_cloud_cpu_hours"], 0)
        self.assertEqual(len(summary["VOs_complete_list"]), 67)
        self.assertEqual(summary["VOs_complete_list"][0]["VO name"], "ALICE")
        self.assertEqual(summary["VOs_complete_list"][0]["CPU/h"], " 17,664")

if __name__ == '__main__':
    unittest.main()