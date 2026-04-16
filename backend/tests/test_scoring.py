import unittest

from app.domain.geometry import encode_polyline
from app.domain.scoring import score_routes
from app.schemas.models import GoogleRoute, LatLngLiteral, PollenSignal, UserProfile, WeatherSignal

WEATHER = WeatherSignal(
    description="Breezy and dry",
    windSpeedMph=12,
    humidity=46,
    temperatureF=66,
)

POLLEN = PollenSignal(
    treeIndex=4,
    grassIndex=1,
    weedIndex=1,
    summary="Tree pollen elevated",
)


def build_route(route_id: str, points: list[tuple[float, float]], duration_min: float, distance_meters: float):
    return GoogleRoute(
        id=route_id,
        polyline=encode_polyline([LatLngLiteral(lat=lat, lng=lng) for lat, lng in points]),
        durationMin=duration_min,
        distanceMeters=distance_meters,
    )


class ScoreRoutesTests(unittest.TestCase):
    month = 3

    def test_increases_exposure_when_trigger_overlap_is_stronger(self):
        route = build_route(
            "r1",
            [(40.772, -73.985), (40.788, -73.983)],
            18,
            1800,
        )

        mild_profile = UserProfile(
            triggers=[],
            sensitivity="medium",
            knowsTreeTriggers=False,
        )
        tree_profile = UserProfile(
            triggers=["oak"],
            sensitivity="medium",
            knowsTreeTriggers=True,
        )

        mild_score = score_routes([route], mild_profile, WEATHER, POLLEN, current_month=self.month)[0]["candidate"].exposureScore
        tree_score = score_routes([route], tree_profile, WEATHER, POLLEN, current_month=self.month)[0]["candidate"].exposureScore

        self.assertGreater(tree_score, mild_score)

    def test_can_rank_a_longer_lower_burden_route_above_a_shorter_higher_burden_route(self):
        risky_route = build_route(
            "risky",
            [(40.776, -73.985), (40.789, -73.984)],
            15,
            1500,
        )
        safer_route = build_route(
            "safer",
            [(40.752, -73.998), (40.764, -73.97)],
            22,
            2500,
        )
        profile = UserProfile(
            triggers=["oak"],
            sensitivity="medium",
            knowsTreeTriggers=True,
        )

        best = score_routes([risky_route, safer_route], profile, WEATHER, POLLEN, current_month=self.month)[0]
        self.assertEqual(best["candidate"].id, "safer")

    def test_raises_scores_for_highly_sensitive_users(self):
        route = build_route(
            "r1",
            [(40.74, -73.984), (40.752, -73.97)],
            16,
            1600,
        )
        low_sensitivity = UserProfile(
            triggers=["maple"],
            sensitivity="low",
            knowsTreeTriggers=True,
        )
        high_sensitivity = UserProfile(
            triggers=["maple"],
            sensitivity="high",
            knowsTreeTriggers=True,
        )

        low_score = score_routes([route], low_sensitivity, WEATHER, POLLEN, current_month=self.month)[0]["candidate"].exposureScore
        high_score = score_routes([route], high_sensitivity, WEATHER, POLLEN, current_month=self.month)[0]["candidate"].exposureScore

        self.assertGreater(high_score, low_score)

    def test_minimizes_overall_tree_contact_when_tree_triggers_are_unknown(self):
        route = build_route(
            "r1",
            [(40.752, -73.984), (40.776, -73.97)],
            20,
            2100,
        )
        profile = UserProfile(
            triggers=[],
            sensitivity="medium",
            knowsTreeTriggers=False,
        )

        general_score = score_routes([route], profile, WEATHER, POLLEN, current_month=self.month)[0]["candidate"].exposureScore
        self.assertGreater(general_score, 0)

    def test_raises_exposure_when_pollen_and_wind_conditions_intensify(self):
        route = build_route(
            "r1",
            [(40.752, -73.984), (40.776, -73.97)],
            20,
            2100,
        )
        profile = UserProfile(
            triggers=[],
            sensitivity="medium",
            knowsTreeTriggers=False,
        )

        calm_score = score_routes(
            [route],
            profile,
            WeatherSignal(description=WEATHER.description, windSpeedMph=4, humidity=68, temperatureF=56),
            PollenSignal(treeIndex=2, grassIndex=POLLEN.grassIndex, weedIndex=POLLEN.weedIndex, summary=POLLEN.summary),
            current_month=self.month,
        )[0]["candidate"].exposureScore
        intense_score = score_routes(
            [route],
            profile,
            WeatherSignal(description=WEATHER.description, windSpeedMph=18, humidity=32, temperatureF=74),
            PollenSignal(treeIndex=5, grassIndex=POLLEN.grassIndex, weedIndex=POLLEN.weedIndex, summary=POLLEN.summary),
            current_month=self.month,
        )[0]["candidate"].exposureScore

        self.assertGreater(intense_score, calm_score)


if __name__ == "__main__":
    unittest.main()
