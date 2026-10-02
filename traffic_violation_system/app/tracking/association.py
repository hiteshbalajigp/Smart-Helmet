from __future__ import annotations

import math

from app.tracking.models import PersonAssociation, PersonTrack, VehiclePersonAssociation, VehicleTrack
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class VehiclePersonAssociator:
    def __init__(self, *, threshold: float = 0.45) -> None:
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("association threshold must be between 0 and 1")
        self.threshold = threshold
        self._previous_vehicle_by_person: dict[int, int] = {}
        self._association_failures = 0

    @staticmethod
    def _spatial_score(person: PersonTrack, vehicle: VehicleTrack) -> tuple[float, float, float]:
        person_box = person.bounding_box
        vehicle_box = vehicle.bounding_box
        px = person_box.center_x
        py = person_box.y2

        nearest_x = min(max(px, vehicle_box.x1), vehicle_box.x2)
        nearest_y = min(max(py, vehicle_box.y1), vehicle_box.y2)
        diagonal = max(math.hypot(vehicle_box.width, vehicle_box.height), 1.0)
        distance = math.hypot(px - nearest_x, py - nearest_y)
        proximity = max(0.0, 1.0 - distance / (0.75 * diagonal))

        overlap_width = max(0.0, min(person_box.x2, vehicle_box.x2) - max(person_box.x1, vehicle_box.x1))
        overlap_height = max(0.0, min(person_box.y2, vehicle_box.y2) - max(person_box.y1, vehicle_box.y1))
        person_area = max(person_box.width * person_box.height, 1.0)
        overlap = (overlap_width * overlap_height) / person_area
        return 0.7 * proximity + 0.3 * overlap, px, py

    def associate(
        self,
        vehicles: tuple[VehicleTrack, ...],
        people: tuple[PersonTrack, ...],
    ) -> tuple[VehiclePersonAssociation, ...]:
        previous_vehicle_by_person = self._previous_vehicle_by_person
        scores: dict[tuple[int, int], float] = {}
        for person in people:
            for vehicle in vehicles:
                spatial, _, _ = self._spatial_score(person, vehicle)
                temporal = float(previous_vehicle_by_person.get(person.track_id) == vehicle.track_id)
                scores[(person.track_id, vehicle.track_id)] = 0.85 * spatial + 0.15 * temporal

        grouped: dict[int, list[PersonAssociation]] = {vehicle.track_id: [] for vehicle in vehicles}
        next_vehicle_by_person: dict[int, int] = {}
        for person in people:
            candidates = [
                (scores[(person.track_id, vehicle.track_id)], vehicle.track_id, vehicle)
                for vehicle in vehicles
                if scores[(person.track_id, vehicle.track_id)] >= self.threshold
            ]
            if not candidates:
                self._association_failures += 1
                continue
            score, vehicle_id, vehicle = max(candidates, key=lambda item: (item[0], -item[1]))
            grouped[vehicle_id].append(
                PersonAssociation(
                    person_track_id=person.track_id,
                    bounding_box=person.bounding_box,
                    relative_x=(person.bounding_box.center_x - vehicle.bounding_box.center_x)
                    / max(vehicle.bounding_box.width, 1.0),
                    relative_y=(person.bounding_box.center_y - vehicle.bounding_box.center_y)
                    / max(vehicle.bounding_box.height, 1.0),
                    association_score=score,
                )
            )
            next_vehicle_by_person[person.track_id] = vehicle_id

        results: list[VehiclePersonAssociation] = []
        for vehicle in vehicles:
            vehicle_people = tuple(sorted(grouped[vehicle.track_id], key=lambda item: item.person_track_id))
            confidence = (
                sum(person.association_score for person in vehicle_people) / len(vehicle_people)
                if vehicle_people
                else 0.0
            )
            result = VehiclePersonAssociation(
                vehicle_track_id=vehicle.track_id,
                person_track_ids=tuple(person.person_track_id for person in vehicle_people),
                persons=vehicle_people,
                candidate_rider_track_id=None,
                candidate_pillion_track_ids=(),
                unknown_track_ids=tuple(person.person_track_id for person in vehicle_people),
                association_confidence=confidence,
                role_confidence=0.0,
            )
            results.append(result)
            if any(
                previous_vehicle_by_person.get(person_id) != vehicle.track_id
                for person_id in result.person_track_ids
            ):
                logger.info("Vehicle/person association created: vehicle_track_id=%s", vehicle.track_id)

        self._previous_vehicle_by_person = next_vehicle_by_person
        if any(
            person_id not in next_vehicle_by_person
            or next_vehicle_by_person[person_id] != vehicle_id
            for person_id, vehicle_id in previous_vehicle_by_person.items()
        ):
            logger.info("Vehicle/person association removed or changed.")
        return tuple(results)

    @property
    def association_failures(self) -> int:
        return self._association_failures
