import unittest

import delete_deleted_torrents as module


class FakeResponse:
    def __init__(self, payload=None, text="Ok."):
        self._payload = payload
        self.text = text

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class DeleteRuleTests(unittest.TestCase):
    def test_all_configured_tracker_rules_match(self):
        examples = (
            (
                "https://aither.cc/announce/example",
                "Torrent has been deleted",
            ),
            (
                "https://hdts-announce.ru/announce.php?pid=example",
                "Torrent is not authorized for use on this tracker.",
            ),
            (
                "https://trackerprxy.digitalcore.club/announce/example",
                "Torrent does not exist on this tracker.",
            ),
        )

        for tracker_url, message in examples:
            with self.subTest(tracker_url=tracker_url):
                self.assertIsNotNone(
                    module.matching_delete_rule(tracker_url, message)
                )

    def test_ncore_domain_and_subdomains_match(self):
        tracker_urls = (
            "http://ncore.sh:2710/example-passkey/announce",
            "http://t.ncore.sh:2710/example-passkey/announce",
            "https://tracker.ncore.sh/example-passkey/announce",
        )

        for tracker_url in tracker_urls:
            with self.subTest(tracker_url=tracker_url):
                self.assertIsNotNone(
                    module.matching_delete_rule(
                        tracker_url,
                        "err: unregistered torrent",
                    )
                )

    def test_similar_but_unconfigured_tracker_does_not_match(self):
        self.assertIsNone(
            module.matching_delete_rule(
                "https://tracker.digitalcore.club/announce/example",
                "Torrent does not exist on this tracker.",
            )
        )

    def test_ncore_lookalike_domain_does_not_match(self):
        lookalike_urls = (
            "http://evilncore.sh:2710/example/announce",
            "http://ncore.sh.example.com/example/announce",
        )

        for tracker_url in lookalike_urls:
            with self.subTest(tracker_url=tracker_url):
                self.assertIsNone(
                    module.matching_delete_rule(
                        tracker_url,
                        "err: unregistered torrent",
                    )
                )

    def test_wrong_message_does_not_match(self):
        self.assertIsNone(
            module.matching_delete_rule(
                "https://hdts-announce.ru/announce.php?pid=example",
                "Announce timed out",
            )
        )

    def test_ncore_other_error_does_not_match(self):
        self.assertIsNone(
            module.matching_delete_rule(
                "http://t.ncore.sh:2710/example-passkey/announce",
                "err: invalid passkey",
            )
        )


class QBittorrentClientTests(unittest.TestCase):
    def test_delete_request_removes_torrent_and_files(self):
        config = module.Config(
            qbit_url="http://127.0.0.1:8080",
            username="user",
            password="secret",
        )
        client = module.QBittorrentClient(config)
        captured = {}

        class FakeSession:
            def post(self, url, data, timeout):
                captured.update(url=url, data=data, timeout=timeout)
                return FakeResponse()

        client.session = FakeSession()
        client.delete_torrent("torrent-hash")

        self.assertEqual(
            captured["url"],
            "http://127.0.0.1:8080/api/v2/torrents/delete",
        )
        self.assertEqual(
            captured["data"],
            {
                "hashes": "torrent-hash",
                "deleteFiles": "true",
            },
        )


class LockTests(unittest.TestCase):
    def test_second_instance_of_same_profile_is_blocked(self):
        first_lock = module.acquire_single_instance_lock("profile-one")
        self.assertIsNotNone(first_lock)
        try:
            second_lock = module.acquire_single_instance_lock("profile-one")
            self.assertIsNone(second_lock)
        finally:
            first_lock.close()

    def test_different_profiles_can_run_at_the_same_time(self):
        first_lock = module.acquire_single_instance_lock("profile-one")
        second_lock = module.acquire_single_instance_lock("profile-two")
        self.assertIsNotNone(first_lock)
        self.assertIsNotNone(second_lock)
        try:
            pass
        finally:
            first_lock.close()
            second_lock.close()


class ArgumentTests(unittest.TestCase):
    def test_dry_run_flag(self):
        args = module.parse_args(["--dry-run"])
        self.assertTrue(args.dry_run)


if __name__ == "__main__":
    unittest.main()
