import json
import os
import logging
from unittest.mock import patch
import pandas as pd
import pytest
import requests

from awpy.parser import DemoParser


class TestDemoParser:
    """Class to test the match parser

    We use the demofiles in test_data.json
    """

    def setup_class(self):
        """Setup class by defining loading dictionary of test demo files"""
        with open("tests/test_data.json", encoding="utf-8") as f:
            self.demo_data = json.load(f)
        for file in self.demo_data:
            self._get_demofile(demo_link=self.demo_data[file]["url"], demo_name=file)
        self.parser = DemoParser(demofile="default.dem", log=False, parse_rate=256)

    def teardown_class(self):
        """Set parser to none, deletes all demofiles and JSON"""
        self.parser = None
        files_in_directory = os.listdir()
        filtered_files = [
            file
            for file in files_in_directory
            if file.endswith(".dem") or file.endswith(".json")
        ]
        if len(filtered_files) > 0:
            for f in filtered_files:
                os.remove(f)

    @staticmethod
    def _get_demofile(demo_link, demo_name):
        print("Requesting " + demo_link)
        r = requests.get(demo_link)
        open(demo_name + ".dem", "wb").write(r.content)

    @staticmethod
    def _delete_demofile(demo_name):
        print("Removing " + demo_name)
        os.remove(demo_name + ".dem")

    @staticmethod
    def _check_round_scores(rounds):
        for i, r in enumerate(rounds):
            if i == 0:
                assert r["tScore"] == 0
                assert r["ctScore"] == 0
            if i > 0 and i != len(rounds):
                winningSide = rounds[i - 1]["winningSide"]
                if winningSide == "ct":
                    assert r["ctScore"] > rounds[i - 1]["ctScore"]
                    assert r["tScore"] == rounds[i - 1]["tScore"]
                if winningSide == "t":
                    assert r["ctScore"] == rounds[i - 1]["ctScore"]
                    assert r["tScore"] > rounds[i - 1]["tScore"]

    def test_demo_id_inferred(self):
        """Tests if a demo_id is correctly inferred"""
        self.parser_inferred = DemoParser(
            demofile="default.dem",
            log=False,
        )
        assert self.parser_inferred.demo_id == "default"
        self.parser_inferred = DemoParser(demofile=r"D:/CSGO/Demos/800.dem", log=False)
        assert self.parser_inferred.demo_id == "800"
        self.parser_inferred = DemoParser(demofile=r"D:\CSGO\Demos\900.dem", log=False)
        assert self.parser_inferred.demo_id == "900"

    def test_outpath(self):
        """Tests if the outpath is correctly recorded"""
        self.parser_outpath = DemoParser(demofile="default.dem", log=False, outpath=".")
        assert self.parser_outpath.outpath == os.getcwd()

    def test_demo_id_given(self):
        """Tests if a demo_id is correctly set"""
        self.parser_inferred = DemoParser(
            demofile="default.dem",
            demo_id="test",
            log=False,
        )
        assert self.parser_inferred.demo_id == "test"

    def test_wrong_demo_path(self):
        """Tests if failure on wrong demofile path"""
        with pytest.raises(FileNotFoundError):
            self.parser_wrong_demo_path = DemoParser(
                demofile="bad.dem",
                log=False,
                demo_id="test",
                parse_rate=128,
            )
            self.parser_wrong_demo_path.parse()

    def test_parse_rate(self):
        """Tests if bad parse rates fail"""
        self.parser_neg_parse_rate = DemoParser(
            demofile="default.dem",
            log=False,
            demo_id="test",
            parse_rate=-1,
        )
        assert self.parser_neg_parse_rate.parse_rate == 128
        self.parser_float_parse_rate = DemoParser(
            demofile="default.dem",
            log=False,
            demo_id="test",
            parse_rate=64.5,
        )
        assert self.parser_float_parse_rate.parse_rate == 128
        self.parser_good_parse_rate = DemoParser(
            demofile="default.dem",
            log=False,
            demo_id="test",
            parse_rate=16,
        )
        assert self.parser_good_parse_rate.parse_rate == 16
        self.parser_inferred_parse_rate = DemoParser(
            demofile="default.dem",
            log=False,
            demo_id="test",
        )
        assert self.parser_inferred_parse_rate.parse_rate == 128

    def test_logger_set(self):
        """Tests if log file is created"""
        assert self.parser.logger.name == "awpy"

    def test_parse_opts(self, caplog):
        """Tests parsing options"""
        caplog.set_level(logging.WARNING)
        self.parser_opts = DemoParser(
            demofile="default.dem",
            log=True,
            demo_id="test",
            trade_time=8,
            buy_style="hltv",
            dmg_rolled=True,
            json_indentation=True,
        )
        assert self.parser_opts.trade_time == 8
        assert self.parser_opts.buy_style == "hltv"
        assert self.parser_opts.parse_frames is True
        assert self.parser_opts.dmg_rolled is True
        assert self.parser_opts.json_indentation is True
        assert self.parser_opts.parse_kill_frames is False
        assert (
            "Trade time of 8 is rather long. Consider a value between 4-7."
            in caplog.text
        )
        self.bad_parser_opts = DemoParser(
            demofile="default.dem",
            log=True,
            demo_id="test",
            trade_time=-2,
            buy_style="test",
        )
        assert self.bad_parser_opts.trade_time == 5

        assert self.bad_parser_opts.buy_style == "hltv"
        assert (
            "Trade time can't be negative, setting to default value of 5 seconds."
            in caplog.text
        )

    def test_read_json_bad_path(self):
        """Tests if the read_json fails on bad path"""
        p = DemoParser()
        with pytest.raises(FileNotFoundError):
            p.read_json("bad_json.json")

    def test_parse_output_type(self):
        """Tests if the JSON output from parse is a dict"""
        output_json = self.parser.parse()
        assert isinstance(output_json, dict)
        assert os.path.exists("default.json")
        assert self.parser.output_file == "default.json"
        assert self.parser.parse_error is False

    def test_parse_valve_matchmaking(self):
        """Tests if demos parse correctly"""
        self.valve_mm = DemoParser(
            demofile="valve_matchmaking.dem",
            log=False,
            parse_rate=256,
        )
        self.valve_mm_data = self.valve_mm.parse()
        assert len(self.valve_mm_data["gameRounds"]) == 25  # 26

    def test_ot_demos(self):
        """Test overtime demos"""
        self.faceit_ot = DemoParser(
            demofile="faceit_ecs_ot.dem", log=False, parse_rate=256
        )
        self.faceit_ot_data = self.faceit_ot.parse()
        assert len(self.faceit_ot_data["gameRounds"]) > 30
        assert self.faceit_ot_data["tickRate"] == 128

    def test_default_parse(self):
        """Tests default parse"""
        self.default_data = self.parser.parse()
        assert self.default_data["mapName"] == "de_cache"
        assert self.default_data["tickRate"] == 128
        assert self.default_data["clientName"] == "GOTV Demo"
        assert len(self.default_data["gameRounds"]) == 29  # 33
        assert self.default_data["parserParameters"]["damagesRolledUp"] is False
        assert self.default_data["parserParameters"]["tradeTime"] == 5
        assert self.default_data["parserParameters"]["roundBuyStyle"] == "hltv"
        assert self.default_data["parserParameters"]["parseRate"] == 256
        for r in self.default_data["gameRounds"]:
            assert isinstance(r["bombEvents"], list)
            assert isinstance(r["damages"], list)
            assert isinstance(r["kills"], list)
            assert isinstance(r["flashes"], list)
            assert isinstance(r["grenades"], list)
            assert isinstance(r["weaponFires"], list)
            assert isinstance(r["frames"], list)

    def test_parse_kill_frames(self):
        """Tests parse kill frames"""
        self.parser_kill_frames = DemoParser(
            demofile="default.dem",
            log=False,
            parse_frames=False,
            parse_kill_frames=True,
        )
        self.default_data = self.parser_kill_frames.parse()
        for r in self.default_data["gameRounds"]:
            assert len(r["kills"]) == len(r["frames"])

    def test_default_parse_df(self):
        """Tests default parse to dataframe"""
        self.default_data_df = self.parser.parse(return_type="df")
        assert isinstance(self.default_data_df["rounds"], pd.DataFrame)
        assert isinstance(self.default_data_df["kills"], pd.DataFrame)
        assert isinstance(self.default_data_df["damages"], pd.DataFrame)
        assert isinstance(self.default_data_df["grenades"], pd.DataFrame)
        assert isinstance(self.default_data_df["flashes"], pd.DataFrame)
        assert isinstance(self.default_data_df["weaponFires"], pd.DataFrame)
        assert isinstance(self.default_data_df["bombEvents"], pd.DataFrame)
        assert isinstance(self.default_data_df["frames"], pd.DataFrame)
        assert isinstance(self.default_data_df["playerFrames"], pd.DataFrame)
        self.parser.json = None
        with pytest.raises(AttributeError):
            self.parser.parse_json_to_df()

    def test_wrong_return_type(self):
        """Tests if wrong return type errors out"""
        with pytest.raises(ValueError):
            d = self.parser.parse(return_type="i_am_wrong")

    def test_bot_name(self):
        """Tests if bot naming is correct (brought up by Charmees).
        Original error had "Troy" (bot) showing up instead of "Charmees" (player)
        """
        self.bot_name_parser = DemoParser(
            demofile="bot_name_test.dem", log=False, parse_frames=False
        )
        self.bot_name_data = self.bot_name_parser.parse()
        charmees_found = 0
        for r in self.bot_name_data["gameRounds"]:
            if r["damages"]:
                for e in r["damages"]:
                    if e["victimName"] == "Charmees":
                        charmees_found += 1
        assert charmees_found > 0

    def test_remove_bad_scoring(self):
        """Tests if remove bad scoring works. Issue 149 raised by kenmareirl"""
        self.bad_scoring_parser_bad_demo = DemoParser(
            demofile="anonymo-vs-ldlc-m1-nuke.dem", log=False, parse_frames=False
        )
        self.bad_scoring_parser_data = self.bad_scoring_parser_bad_demo.parse()
        self.bad_scoring_parser_data = self.bad_scoring_parser_bad_demo.clean_rounds(
            remove_bad_scoring=True,
        )
        assert len(self.bad_scoring_parser_data["gameRounds"]) == 26
        self.bad_scoring_parser_good_demo = DemoParser(
            demofile="valve_matchmaking.dem", log=False, parse_frames=False
        )
        self.bad_scoring_parser_data_good = self.bad_scoring_parser_good_demo.parse()
        self.bad_scoring_parser_data_good = (
            self.bad_scoring_parser_good_demo.clean_rounds(
                remove_bad_scoring=True,
            )
        )
        assert len(self.bad_scoring_parser_data["gameRounds"]) == 26

    def test_warmup(self):
        """Tests if warmup rounds are properly parsing."""
        self.warmup_parser = DemoParser(
            demofile="warmup_test.dem", log=False, parse_frames=False
        )
        self.warmup_data = self.warmup_parser.parse()
        self.warmup_data = self.warmup_parser.clean_rounds(
            remove_no_frames=False,
            remove_excess_players=False,
        )
        assert len(self.warmup_data["gameRounds"]) == 30
        self._check_round_scores(self.warmup_data["gameRounds"])
        self.warmup_parser_sneem = DemoParser(
            demofile="vitality-vs-g2-m2-mirage.dem", log=False, parse_frames=True
        )
        self.warmup_sneem_data = self.warmup_parser_sneem.parse()
        self.warmup_sneem_data = self.warmup_parser_sneem.clean_rounds(
            remove_excess_players=False,
        )
        assert len(self.warmup_sneem_data["gameRounds"]) == 30
        self._check_round_scores(self.warmup_sneem_data["gameRounds"])

    def test_bomb_sites(self):
        """Tests that both bombsite A and B show up."""
        self.bombsite_parser = DemoParser(
            demofile="bombsite_test.dem", log=False, parse_frames=False
        )
        self.bombsite_data = self.bombsite_parser.parse()
        for r in self.bombsite_data["gameRounds"]:
            for e in r["bombEvents"]:
                assert (e["bombSite"] == "A") or (e["bombSite"] == "B")

    def test_phase_lists(self):
        """Tests that phase lists are lists."""
        self.phase_parser = DemoParser(
            demofile="bombsite_test.dem", log=False, parse_frames=False
        )
        self.phase_data = self.phase_parser.parse()
        for phase in self.phase_data["matchPhases"].keys():
            assert isinstance(self.phase_data["matchPhases"][phase], list)

    def test_round_clean(self):
        """Tests that remove time rounds is working."""
        self.round_clean_parser = DemoParser(
            demofile="round_clean_test.dem", log=False, parse_frames=False
        )
        self.round_clean_data = self.round_clean_parser.parse()
        self.round_clean_parser.remove_time_rounds()
        assert len(self.round_clean_data["gameRounds"]) == 24

    def test_clean_return_type(self):
        """Tests clean_rounds has correct return type."""
        self.clean_return_parser = DemoParser(
            demofile="default.dem",
            log=False,
            parse_rate=256,
            dmg_rolled=True,
            json_indentation=True,
        )
        _ = self.clean_return_parser.parse()
        df_return = self.clean_return_parser.clean_rounds(return_type="df")
        assert isinstance(df_return["rounds"], pd.DataFrame)
        assert isinstance(df_return["kills"], pd.DataFrame)
        assert isinstance(df_return["damages"], pd.DataFrame)
        assert isinstance(df_return["grenades"], pd.DataFrame)
        assert isinstance(df_return["flashes"], pd.DataFrame)
        assert isinstance(df_return["weaponFires"], pd.DataFrame)
        assert isinstance(df_return["bombEvents"], pd.DataFrame)
        assert isinstance(df_return["frames"], pd.DataFrame)
        assert isinstance(df_return["playerFrames"], pd.DataFrame)
        dict_return = self.clean_return_parser.clean_rounds(return_type="json")
        assert isinstance(dict_return, dict)
        with pytest.raises(ValueError):
            self.clean_return_parser.clean_rounds(
                return_type="return_type_does_not_exist"
            )

    def test_player_clean(self):
        """Tests that remove excess players is working."""
        self.player_clean_parser = DemoParser(
            demofile="pov-clean.dem", log=False, parse_frames=True
        )
        self.player_clean_data = self.player_clean_parser.parse()
        self.player_clean_parser.remove_excess_players()
        assert len(self.player_clean_data["gameRounds"]) == 23  # 28
        test_json = {
            "gameRounds": [
                # Both players None -> remove
                {"frames": [{"ct": {"players": None}, "t": {"players": None}}]},
                # One None the other valid -> keep
                {"frames": [{"ct": {"players": None}, "t": {"players": [1, 2, 3]}}]},
                # One none the other invalid -> remove
                {
                    "frames": [
                        {"ct": {"players": None}, "t": {"players": [1, 2, 3, 4, 5, 6]}}
                    ]
                },
                # One None the other valid -> keep
                {"frames": [{"ct": {"players": [1, 2, 3]}, "t": {"players": None}}]},
                # Both valid -> keep
                {
                    "frames": [
                        {"ct": {"players": [1, 2, 3]}, "t": {"players": [1, 2, 3]}}
                    ]
                },
                # First valid second invalid -> remove
                {
                    "frames": [
                        {
                            "ct": {"players": [1, 2, 3]},
                            "t": {"players": [1, 2, 3, 4, 5, 6]},
                        }
                    ]
                },
                # One none the other invalid -> remove
                {
                    "frames": [
                        {"ct": {"players": [1, 2, 3, 4, 5, 6]}, "t": {"players": None}}
                    ]
                },
                # First valid second invalid -> remove
                {
                    "frames": [
                        {
                            "ct": {"players": [1, 2, 3, 4, 5, 6]},
                            "t": {"players": [1, 2, 3]},
                        }
                    ]
                },
                # Both invalid -> remove
                {
                    "frames": [
                        {
                            "ct": {"players": [1, 2, 3, 4, 5, 6]},
                            "t": {"players": [1, 2, 3, 4, 5, 6]},
                        }
                    ]
                },
            ],
        }
        self.player_clean_parser.json = test_json
        self.player_clean_parser.remove_excess_players()
        assert len(self.player_clean_parser.json["gameRounds"]) == 3

    def test_zero_kills(self):
        """Tests a demo that raised many errors"""
        self.zero_kills_parser = DemoParser(
            demofile="nip-vs-gambit-m2-inferno.dem", log=False, parse_rate=256
        )
        self.zero_kills_data = self.zero_kills_parser.parse()
        assert len(self.zero_kills_data["gameRounds"]) == 22

    def test_end_round_cleanup(self):
        """Tests cleaning the last round"""
        self.end_round_parser = DemoParser(
            demofile="vitality-vs-ence-m1-mirage.dem", log=False, parse_rate=256
        )
        self.end_round_data = self.end_round_parser.parse()
        assert len(self.end_round_data["gameRounds"]) == 30

    def test_clean_no_json(self):
        """Tests cleaning when parser.json is not set or None"""
        self.no_json_parser = DemoParser(
            demofile="vitality-vs-ence-m1-mirage.dem", log=False, parse_rate=256
        )
        with pytest.raises(AttributeError):
            self.no_json_parser.clean_rounds()
        self.no_json_parser.json = None
        with pytest.raises(AttributeError):
            self.no_json_parser.clean_rounds()

    def test_esea_ot_demo(self):
        """Tests an ESEA demo with OT rounds"""
        self.esea_ot_parser = DemoParser(
            demofile="esea_match_16902209.dem", log=False, parse_rate=256
        )
        self.esea_ot_data = self.esea_ot_parser.parse()
        assert len(self.esea_ot_data["gameRounds"]) == 35

    @patch("os.path.isfile")
    def test_parse_demo_error(self, isfile_mock):
        """Tests if parser sets parse_error correctly
        if not outputfile can be found"""
        isfile_mock.return_value = False
        self.parser.parse_demo()
        assert self.parser.parse_error is True

    @patch("awpy.parser.demoparser.check_go_version")
    def test_bad_go_version(self, go_version_mock):
        """Tests parse_demo fails on bad go version"""
        go_version_mock.return_value = False
        with pytest.raises(ValueError):
            self.parser.parse_demo()

    def test_parse_error(self):
        """Tests if parser raises an AttributeError if the json attribute does not get set"""
        error_parser = DemoParser(demofile="default.dem", log=False, parse_rate=256)
        error_parser.json = None
        with patch.object(error_parser, "read_json") as read_mock:
            with patch.object(error_parser, "parse_demo") as parse_mock:
                with pytest.raises(AttributeError):
                    error_parser.parse(clean=False)
                assert parse_mock.call_count == 1
                assert read_mock.call_count == 1

    def test_no_json(self):
        """Tests if parser raises an AttributeError if the json attribute does not get set"""
        no_json_parser = DemoParser(demofile="default.dem", log=False, parse_rate=256)
        # Json ist set but falsy
        no_json_parser.json = None
        with pytest.raises(AttributeError):
            no_json_parser._parse_frames()
        with pytest.raises(AttributeError):
            no_json_parser._parse_player_frames()
        with pytest.raises(AttributeError):
            no_json_parser._parse_rounds()
        with pytest.raises(AttributeError):
            no_json_parser._parse_weapon_fires()
        with pytest.raises(AttributeError):
            no_json_parser._parse_kills()
        with pytest.raises(AttributeError):
            no_json_parser._parse_damages()
        with pytest.raises(AttributeError):
            no_json_parser._parse_grenades()
        with pytest.raises(AttributeError):
            no_json_parser._parse_bomb_events()
        with pytest.raises(AttributeError):
            no_json_parser._parse_flashes()
        with pytest.raises(AttributeError):
            no_json_parser.remove_bad_scoring()
        with pytest.raises(AttributeError):
            no_json_parser.remove_rounds_with_no_frames()
        with pytest.raises(AttributeError):
            no_json_parser.remove_excess_players()
        with pytest.raises(AttributeError):
            no_json_parser.remove_end_round()
        with pytest.raises(AttributeError):
            no_json_parser.remove_warmups()
        with pytest.raises(AttributeError):
            no_json_parser.remove_knife_rounds()
        with pytest.raises(AttributeError):
            no_json_parser.remove_excess_kill_rounds()
        with pytest.raises(AttributeError):
            no_json_parser.remove_time_rounds()
        no_json_parser.json = {"gameRounds": None}
        with pytest.raises(AttributeError):
            no_json_parser.renumber_rounds()
