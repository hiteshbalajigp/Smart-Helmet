from __future__ import annotations

import math

from app.tracking.models import (
    PersonAssociation,
    PersonRole,
    VehiclePersonAssociation,
    VehicleTrack,
)
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class RiderPillionRoleAssigner:
    """Assigns candidates only when spatial evidence and motion direction are sufficient."""

    def __init__(self, *, confidence_threshold: float = 0.65) -> None:
        if not 0.0 <= confidence_threshold <= 1.0:
            raise ValueError("role confidence threshold must be between 0 and 1")
        self.confidence_threshold = confidence_threshold
        self._previous_roles: dict[int, tuple[tuple[int, ...], int, tuple[int, ...], float]] = {}

    def assign(
        self,
        associations: tuple[VehiclePersonAssociation, ...],
        vehicles: tuple[VehicleTrack, ...],
    ) -> tuple[VehiclePersonAssociation, ...]:
        vehicle_by_id = {vehicle.track_id: vehicle for vehicle in vehicles}
        results: list[VehiclePersonAssociation] = []
        live_vehicle_ids = set(vehicle_by_id)

        for association in associations:
            vehicle = vehicle_by_id.get(association.vehicle_track_id)
            if vehicle is None:
                results.append(association)
                continue

            person_ids = association.person_track_ids
            role_map: dict[int, PersonRole] = {person_id: PersonRole.UNKNOWN for person_id in person_ids}
            rider_id: int | None = None
            pillion_ids: tuple[int, ...] = ()
            role_confidence = 0.0

            previous = self._previous_roles.get(vehicle.track_id)
            if previous and previous[0] == person_ids:
                _, rider_id, pillion_ids, role_confidence = previous
                role_map[rider_id] = PersonRole.RIDER
                for person_id in pillion_ids:
                    role_map[person_id] = PersonRole.PILLION
            elif len(person_ids) == 1:
                only_person = association.persons[0]
                if only_person.association_score >= self.confidence_threshold:
                    rider_id = only_person.person_track_id
                    role_confidence = only_person.association_score
                    role_map[rider_id] = PersonRole.RIDER
            elif len(person_ids) > 1:
                speed = math.hypot(vehicle.velocity_x, vehicle.velocity_y)
                diagonal = max(math.hypot(vehicle.bounding_box.width, vehicle.bounding_box.height), 1.0)
                if speed / diagonal >= 0.02 and association.association_confidence >= self.confidence_threshold:
                    direction_x = vehicle.velocity_x / speed
                    direction_y = vehicle.velocity_y / speed
                    projections = [
                        (
                            person.person_track_id,
                            person.bounding_box.center_x * direction_x
                            + person.bounding_box.center_y * direction_y,
                            person.association_score,
                        )
                        for person in association.persons
                    ]
                    projections.sort(key=lambda item: (item[1], item[0]), reverse=True)
                    lead_gap = projections[0][1] - projections[1][1]
                    normalized_gap = lead_gap / diagonal
                    role_confidence = association.association_confidence * min(normalized_gap / 0.15, 1.0)
                    if normalized_gap >= 0.05 and role_confidence >= self.confidence_threshold:
                        rider_id = projections[0][0]
                        pillion_ids = tuple(sorted(item[0] for item in projections[1:]))
                        role_map[rider_id] = PersonRole.RIDER
                        for person_id in pillion_ids:
                            role_map[person_id] = PersonRole.PILLION

            person_results = tuple(
                PersonAssociation(
                    person_track_id=person.person_track_id,
                    bounding_box=person.bounding_box,
                    relative_x=person.relative_x,
                    relative_y=person.relative_y,
                    association_score=person.association_score,
                    role=role_map[person.person_track_id],
                )
                for person in association.persons
            )
            unknown_ids = tuple(
                person.person_track_id
                for person in person_results
                if person.role == PersonRole.UNKNOWN
            )
            result = VehiclePersonAssociation(
                vehicle_track_id=association.vehicle_track_id,
                person_track_ids=person_ids,
                persons=person_results,
                candidate_rider_track_id=rider_id,
                candidate_pillion_track_ids=pillion_ids,
                unknown_track_ids=unknown_ids,
                association_confidence=association.association_confidence,
                role_confidence=role_confidence,
            )
            if rider_id is not None:
                previous_role = self._previous_roles.get(vehicle.track_id)
                current_role = (
                    person_ids,
                    rider_id,
                    pillion_ids,
                    role_confidence,
                )
                self._previous_roles[vehicle.track_id] = current_role
                if previous_role and previous_role[1:3] != current_role[1:3]:
                    logger.info("Role assignment changed: vehicle_track_id=%s", vehicle.track_id)
            else:
                self._previous_roles.pop(vehicle.track_id, None)
            results.append(result)

        self._previous_roles = {
            vehicle_id: role
            for vehicle_id, role in self._previous_roles.items()
            if vehicle_id in live_vehicle_ids
        }
        return tuple(results)
