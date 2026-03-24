from __future__ import annotations
"""Tests for BeliefParameter enum and RoleProfile model."""

from app.models.role_profile import (
    BeliefParameter,
    RoleType,
    RoleProfile,
    get_role_profile,
)


class TestBeliefParameter:
    """Tests for the BeliefParameter enum."""

    def test_belief_parameter_has_all_seven(self) -> None:
        """Verify there are exactly 7 enum members including PEAK_ENERGY and GUIDANCE_LEVEL."""
        members = list(BeliefParameter)
        assert len(members) == 7
        assert BeliefParameter.PEAK_ENERGY in members
        assert BeliefParameter.GUIDANCE_LEVEL in members
        assert BeliefParameter.DEEP_WORK_TOLERANCE in members
        assert BeliefParameter.CONTEXT_SWITCH_COST in members
        assert BeliefParameter.CHAOS_TOLERANCE in members
        assert BeliefParameter.MEETING_TOLERANCE in members
        assert BeliefParameter.RECOVERY_RATE in members


class TestRoleType:
    """Tests for the RoleType enum."""

    def test_role_type_has_five_roles(self) -> None:
        """Verify there are exactly 5 roles: student, professional, freelancer, manager, creative."""
        members = list(RoleType)
        assert len(members) == 5
        assert RoleType.STUDENT in members
        assert RoleType.PROFESSIONAL in members
        assert RoleType.FREELANCER in members
        assert RoleType.MANAGER in members
        assert RoleType.CREATIVE in members


class TestRoleProfile:
    """Tests for role profile retrieval and default values."""

    def test_get_role_profile_student(self) -> None:
        """Verify Student defaults match expected values."""
        profile = get_role_profile(RoleType.STUDENT)
        assert profile.role == RoleType.STUDENT
        defaults = profile.defaults
        assert defaults[BeliefParameter.PEAK_ENERGY] == 22.0
        assert defaults[BeliefParameter.DEEP_WORK_TOLERANCE] == 45.0
        assert defaults[BeliefParameter.MEETING_TOLERANCE] == 0.3
        assert defaults[BeliefParameter.CONTEXT_SWITCH_COST] == 0.7
        assert defaults[BeliefParameter.CHAOS_TOLERANCE] == 0.4
        assert defaults[BeliefParameter.RECOVERY_RATE] == 0.15
        assert defaults[BeliefParameter.GUIDANCE_LEVEL] == 0.5

    def test_get_role_profile_manager(self) -> None:
        """Verify Manager defaults for key parameters."""
        profile = get_role_profile(RoleType.MANAGER)
        assert profile.role == RoleType.MANAGER
        defaults = profile.defaults
        assert defaults[BeliefParameter.PEAK_ENERGY] == 9.5
        assert defaults[BeliefParameter.MEETING_TOLERANCE] == 0.8
        assert defaults[BeliefParameter.CONTEXT_SWITCH_COST] == 0.3
        assert defaults[BeliefParameter.CHAOS_TOLERANCE] == 0.7

    def test_get_role_profile_creative(self) -> None:
        """Verify Creative defaults for key parameters."""
        profile = get_role_profile(RoleType.CREATIVE)
        assert profile.role == RoleType.CREATIVE
        defaults = profile.defaults
        assert defaults[BeliefParameter.PEAK_ENERGY] == 23.5
        assert defaults[BeliefParameter.DEEP_WORK_TOLERANCE] == 120.0
        assert defaults[BeliefParameter.CONTEXT_SWITCH_COST] == 0.8

    def test_role_profile_has_default_policies(self) -> None:
        """Verify Student has >=2 default policies, one mentioning '2am' or 'late'."""
        profile = get_role_profile(RoleType.STUDENT)
        assert len(profile.default_policies) >= 2

        # At least one policy should mention late-night scheduling
        late_night_found = False
        for policy in profile.default_policies:
            assert "description" in policy
            assert "condition" in policy
            assert "action" in policy
            desc = policy["description"].lower()
            if "2am" in desc or "late" in desc:
                late_night_found = True
        assert late_night_found, "Expected at least one policy mentioning '2am' or 'late'"

    def test_all_roles_have_all_parameters(self) -> None:
        """Verify every role profile has a value for every BeliefParameter."""
        for role in RoleType:
            profile = get_role_profile(role)
            for param in BeliefParameter:
                assert param in profile.defaults, (
                    f"Role {role.value} missing parameter {param.value}"
                )
