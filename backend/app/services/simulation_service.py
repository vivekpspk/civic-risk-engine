"""
simulation_service.py
Generates the reproducible 140-report synthetic dataset across a 3-hour storm window,
clusters related complaints into master incidents, and runs the risk & priority engine.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
from sqlalchemy.orm import Session

from app.models.database import IncidentModel, ReportModel, AssessmentModel
from app.models.schemas import CreateIncidentRequest, FactorInputsSchema
from app.services.incident_service import IncidentService


class SimulationService:
    @staticmethod
    def run_140_reports_simulation(db: Session) -> Dict[str, Any]:
        """
        Executes the full 140-report Challenge 10 stress test:
        - 28 reports: School manhole cluster (St. Jude's High School)
        - 36 reports: Ward boundary waterlogging (Ward 7 / Ward 8 line)
        - 32 reports: Coordinated false-report attack (plus 1 genuine nearby emergency preserved!)
        - 44 reports: Other distributed routine civic issues
        Total = Exactly 140 reports.
        """
        base_time = datetime(2026, 10, 24, 4, 0, 0, tzinfo=timezone.utc)

        # Clear previous simulation data to avoid test interference
        db.query(ReportModel).delete()
        db.query(AssessmentModel).delete()
        db.query(IncidentModel).delete()
        db.commit()

        reports_created: List[ReportModel] = []

        # =====================================================================
        # 1. GROUP A: 28 REPORTS — SCHOOL OPEN MANHOLE CLUSTER
        # =====================================================================
        cluster_a_id = "CL-SCHOOL-MANHOLE"
        incident_a_id = "INC-101-SCHOOL-MANHOLE"

        school_texts = [
            "Deep open gutter lid broken near school entrance",
            "Manhole open near school bus stop, kids walking by",
            "Dangerous uncovered drain chamber on road",
            "Missing manhole cover right at St. Jude's main gate",
            "Big sewer lid displaced by flood water near school crosswalk",
            "Uncovered manhole filled with muddy water, extreme hazard",
            "Pothole? No, dangerous 4-foot deep open manhole near primary gate",
            "Kids could fall into open storm drain chamber near school corner",
            "Manhole open on sidewalk in front of school",
            "Storm drain lid missing, heavy rain pouring in",
            "Open drain near school crosswalk needs immediate barricade",
            "Chamber lid dislodged by water pressure near St. Jude's",
            "Uncovered manhole dangerous for cyclists and children",
            "Big open hole on main road right where school buses turn",
            "Open sewer chamber flooded, completely invisible under puddle",
            "Urgent: Open manhole outside St. Jude's school gate 2",
            "Drain cover washed away in rain, deep hole exposed",
            "Open manhole with swirling water, kids playing nearby",
            "Severe hazard: open manhole lid broken on sidewalk",
            "Chamber open near school playground boundary wall",
            "Uncovered drain hole in front of school stationery shop",
            "Manhole cover missing, please send repair team immediately",
            "Deep open manhole chamber on school road flooded",
            "Broken manhole rim, open drop into storm drain",
            "Open drain hole outside school gate 1",
            "Dangerous sewer hole uncovered near school bus bay",
            "Water overflowing from open manhole chamber near school crossing",
            "Immediate alert: open manhole chamber uncovered at St. Jude's road"
        ]
        assert len(school_texts) == 28, f"Group A must have exactly 28 reports, got {len(school_texts)}"

        for idx, text in enumerate(school_texts, start=1):
            t_offset = idx * 3.5  # Arrives within first 100 minutes
            r = ReportModel(
                report_id=f"REP-A-{idx:03d}",
                incident_id=incident_a_id,
                cluster_id=cluster_a_id,
                reporter_token=f"TOK-SCH-{idx:04d}",
                hazard_type="open_manhole",
                raw_text=text,
                ward="Ward 07",
                latitude=16.5080 + (idx * 0.00005),
                longitude=80.6490 + (idx * 0.00005),
                submitted_at=base_time + timedelta(minutes=t_offset),
                is_flagged_abuse=False,
            )
            reports_created.append(r)

        # Create master clustered incident for Group A
        inc_a = CreateIncidentRequest(
            incident_id=incident_a_id,
            hazard_type="open_manhole",
            title="CRITICAL HAZARD: Open Manhole Chamber @ St. Jude's School Gate",
            description="28 citizen reports merged into unified incident cluster. Missing manhole cover in active school pedestrian zone.",
            ward="Ward 07",
            latitude=16.5082,
            longitude=80.6492,
            created_at=base_time + timedelta(minutes=4),
            evidence_status="corroborated",
            sla_deadline=base_time + timedelta(hours=2),
            assigned_department="Stormwater & Underground Drainage Dept",
            factors=FactorInputsSchema(
                hazard_severity=1.0,               # Fall hazard into sewer
                sensitive_site_proximity=0.95,     # <50m from school gate
                population_exposed=0.85,           # High student footfall
                weather_risk=0.90,                 # 64mm/hr cloudburst
                time_outstanding=0.35,            # Active for ~50m
                recurrence=0.80                    # Repeat lid displacement
            )
        )
        IncidentService.create_incident(db, inc_a)

        # =====================================================================
        # 2. GROUP B: 36 REPORTS — WARD BOUNDARY WATERLOGGING DISPUTE
        # =====================================================================
        cluster_b_id = "CL-BOUNDARY-WATERLOG"
        incident_b_id = "INC-202-BOUNDARY-WATERLOG"

        boundary_texts = [
            f"Knee deep waterlogging on Ward 7 / Ward 8 boundary road near junction #{i}"
            for i in range(1, 37)
        ]
        assert len(boundary_texts) == 36, f"Group B must have exactly 36 reports, got {len(boundary_texts)}"

        for idx, text in enumerate(boundary_texts, start=1):
            t_offset = 15 + idx * 4.0
            r = ReportModel(
                report_id=f"REP-B-{idx:03d}",
                incident_id=incident_b_id,
                cluster_id=cluster_b_id,
                reporter_token=f"TOK-BND-{idx:04d}",
                hazard_type="shallow_waterlogging",
                raw_text=text,
                ward="Ward 07 / Ward 08 Boundary",
                latitude=16.5120 + (idx * 0.00008),
                longitude=80.6550 + (idx * 0.00008),
                submitted_at=base_time + timedelta(minutes=t_offset),
                is_flagged_abuse=False,
            )
            reports_created.append(r)

        # Create master incident for Group B (with an overdue SLA to trigger SLA breach alert!)
        inc_b = CreateIncidentRequest(
            incident_id=incident_b_id,
            hazard_type="severe_flooding",
            title="BOUNDARY DISPUTE: 2.5ft Waterlogging on Ward 7 / Ward 8 Border Arterial",
            description="36 citizen reports. Roads Dept and Stormwater Dept disputing culvert ownership. SLA breached during inter-departmental ping-pong.",
            ward="Ward 07 / 08 Boundary",
            latitude=16.5135,
            longitude=80.6565,
            created_at=base_time + timedelta(minutes=15),
            evidence_status="corroborated",
            # Intentionally set deadline to past relative to simulated base + 3 hours to demonstrate SLA escalation
            sla_deadline=base_time + timedelta(minutes=90),
            assigned_department="Roads & Infrastructure (Lead) + Stormwater (Supporting)",
            factors=FactorInputsSchema(
                hazard_severity=0.75,
                sensitive_site_proximity=0.45,
                population_exposed=0.75,
                weather_risk=0.85,
                time_outstanding=0.70,
                recurrence=0.50
            )
        )
        IncidentService.create_incident(db, inc_b)

        # =====================================================================
        # 3. GROUP C: 32 REPORTS — COORDINATED BOT SPAM + 1 GENUINE PRESERVED INCIDENT
        # =====================================================================
        # 31 synthetic bot reports attacking rival market + 1 genuine nearby emergency
        cluster_c_bot = "CL-BOT-ATTACK"
        incident_c_bot_id = "INC-303-SUSPICIOUS-SPAM"

        for idx in range(1, 32):  # 31 bot reports
            r = ReportModel(
                report_id=f"REP-C-{idx:03d}",
                incident_id=incident_c_bot_id,
                cluster_id=cluster_c_bot,
                reporter_token=f"TOK-SPAM-{idx:04d}",
                hazard_type="garbage_dump",
                raw_text=f"Rival ward market trash dump overflowing horrible smell report #{idx} - shut them down",
                ward="Ward 08",
                latitude=16.5250,
                longitude=80.6650,
                submitted_at=base_time + timedelta(minutes=60 + (idx * 0.2)),  # Burst within 6 minutes!
                is_flagged_abuse=True,
                abuse_reason="Velocity burst: 31 submissions in 6 minutes from coordinated IP subnet",
            )
            reports_created.append(r)

        # 32nd report in Group C: An independent genuine emergency in nearby Ward 8!
        incident_c_genuine_id = "INC-304-GENUINE-ELECTRICAL"
        rep_genuine = ReportModel(
            report_id="REP-C-032",
            incident_id=incident_c_genuine_id,
            cluster_id="CL-GENUINE-ELECTRICAL",
            reporter_token="TOK-CITIZEN-9921",
            hazard_type="exposed_electrical_hazard",
            raw_text="LIVE SPARKING WIRE hanging into flooded street near Ward 8 hospital pharmacy! Major shock hazard!",
            ward="Ward 08",
            latitude=16.5210,
            longitude=80.6610,
            submitted_at=base_time + timedelta(minutes=75),
            is_flagged_abuse=False,
        )
        reports_created.append(rep_genuine)
        assert len([r for r in reports_created if r.report_id.startswith("REP-C")]) == 32, "Group C must have 32 reports"

        # Create incident for the suspicious bot flood (quarantined, lower risk score)
        inc_c_bot = CreateIncidentRequest(
            incident_id=incident_c_bot_id,
            hazard_type="garbage_dump",
            title="SUSPICIOUS REVIEW QUEUE: Coordinated Trash Complaints (Ward 8 Market)",
            description="31 identical template reports flagged by Velocity Anomaly Detector. Quarantined for auditor sign-off. Suspicion is not proof; preserved without deletion.",
            ward="Ward 08",
            latitude=16.5250,
            longitude=80.6650,
            created_at=base_time + timedelta(minutes=60),
            evidence_status="reported",
            sla_deadline=base_time + timedelta(hours=8),
            assigned_department="Auditor Review Queue",
            factors=FactorInputsSchema(
                hazard_severity=0.25,
                sensitive_site_proximity=0.15,
                population_exposed=0.30,
                weather_risk=0.40,
                time_outstanding=0.20,
                recurrence=0.10
            )
        )
        IncidentService.create_incident(db, inc_c_bot)

        # Create incident for the GENUINE hazard in the attack zone (must trigger CRITICAL safety override!)
        inc_c_genuine = CreateIncidentRequest(
            incident_id=incident_c_genuine_id,
            hazard_type="exposed_electrical_hazard",
            title="CRITICAL HAZARD: Live Electrical Sparking Wire in Floodwater",
            description="Independently corroborated citizen report in Ward 8. Sparking power cable immersed in rainwater outside hospital pharmacy.",
            ward="Ward 08",
            latitude=16.5210,
            longitude=80.6610,
            created_at=base_time + timedelta(minutes=75),
            evidence_status="corroborated",
            sla_deadline=base_time + timedelta(hours=1),
            assigned_department="Electricity Board & Emergency Rescue",
            factors=FactorInputsSchema(
                hazard_severity=1.0,               # High voltage shock
                sensitive_site_proximity=0.85,     # Near hospital pharmacy
                population_exposed=0.75,           # Busy shopping sidewalk
                weather_risk=0.90,                 # Submerged in storm puddle
                time_outstanding=0.25,
                recurrence=0.20
            )
        )
        IncidentService.create_incident(db, inc_c_genuine)

        # =====================================================================
        # 4. GROUP D: 44 REPORTS — OTHER ROUTINE CIVIC ISSUES
        # =====================================================================
        routine_types = [
            ("pothole", "Pothole filled with rainwater causing vehicle skid", "Roads Dept", 0.35),
            ("street_light_outage", "Streetlight cluster dark during rainstorm", "Electrical Dept", 0.20),
            ("tree_debris_blocking_road", "Fallen tree branch obstructing left lane", "Parks & Forestry", 0.50),
            ("curb_erosion", "Curb cement crumbling under heavy flow", "Roads Dept", 0.15),
        ]

        for idx in range(1, 45):  # Exactly 44 routine reports
            htype, hdesc, dept, hsev = routine_types[(idx - 1) % len(routine_types)]
            inc_id = f"INC-400-ROUTINE-{idx:02d}"
            r = ReportModel(
                report_id=f"REP-D-{idx:03d}",
                incident_id=inc_id,
                cluster_id=f"CL-ROUTINE-{idx:02d}",
                reporter_token=f"TOK-ROU-{idx:04d}",
                hazard_type=htype,
                raw_text=f"{hdesc} (Location sector #{idx})",
                ward="Ward 07" if idx % 2 == 0 else "Ward 08",
                latitude=16.5000 + (idx * 0.0004),
                longitude=80.6400 + (idx * 0.0004),
                submitted_at=base_time + timedelta(minutes=10 + (idx * 3.5)),
                is_flagged_abuse=False,
            )
            reports_created.append(r)

            # To avoid overloading DB with 44 separate incidents, we cluster every 4 routine reports into 1 ticket
            # 44 reports -> 11 routine grouped tickets
            if idx % 4 == 0 or idx == 44:
                cluster_ticket_id = f"INC-400-ROUTINE-BATCH-{(idx+3)//4:02d}"
                inc_d = CreateIncidentRequest(
                    incident_id=cluster_ticket_id,
                    hazard_type=htype,
                    title=f"Routine Maintenance Batch #{(idx+3)//4:02d}: {htype.replace('_', ' ').title()}",
                    description=f"Grouped routine civic maintenance batch comprising 4 citizen reports in {r.ward}.",
                    ward=r.ward,
                    latitude=r.latitude,
                    longitude=r.longitude,
                    created_at=r.submitted_at,
                    evidence_status="reported",
                    sla_deadline=base_time + timedelta(hours=48),
                    assigned_department=dept,
                    factors=FactorInputsSchema(
                        hazard_severity=hsev,
                        sensitive_site_proximity=0.20,
                        population_exposed=0.30,
                        weather_risk=0.50,
                        time_outstanding=0.15,
                        recurrence=0.10
                    )
                )
                IncidentService.create_incident(db, inc_d)

        # Persist all 140 reports
        db.add_all(reports_created)
        db.commit()

        total_reports_count = len(reports_created)
        assert total_reports_count == 140, f"Expected exactly 140 reports, but got {total_reports_count}"

        # Fetch priority queue and compute dynamic summary statistics
        queue = IncidentService.get_priority_queue(db, limit=100)

        highest_priority_incidents = [
            {
                "queue_rank": item.queue_rank,
                "incident_id": item.incident_id,
                "hazard_type": item.hazard_type,
                "risk_score": item.risk_score,
                "effective_priority_band": item.effective_priority_band,
                "safety_override_active": item.safety_override_active,
                "sla_status": item.sla_status,
                "recommended_action": item.recommended_action,
            }
            for item in queue[:5]
        ]

        overrides_count = sum(1 for it in queue if it.safety_override_active)
        sla_breaches_count = sum(1 for it in queue if it.is_sla_breached)
        missing_data_warnings_count = sum(len(it.uncertainty_warnings) for it in queue)
        distinct_clusters = len(set(r.cluster_id for r in reports_created if r.cluster_id))

        department_assignments = {}
        for it in queue:
            dept = it.assigned_department or "Unassigned"
            department_assignments[dept] = department_assignments.get(dept, 0) + 1

        # Check if genuine hazard (INC-304-GENUINE-ELECTRICAL) remained in top 3 despite bot spam
        genuine_item = next((it for it in queue if it.incident_id == "INC-304-GENUINE-ELECTRICAL"), None)
        genuine_preserved = bool(genuine_item and genuine_item.queue_rank <= 3)

        return {
            "status": "simulation_completed",
            "scenario_name": "IMPACTX 2026 Challenge 10: 140 Reports / 3 Hours Cloudburst",
            "total_reports_ingested": total_reports_count,
            "report_allocations": {
                "school_manhole_reports": 28,
                "boundary_waterlogging_reports": 36,
                "coordinated_bot_attack_reports": 31,
                "genuine_emergency_in_attack_zone": 1,
                "routine_civic_issues_reports": 44,
                "total_verified": 140,
            },
            "proposed_clusters_count": distinct_clusters,
            "incidents_triaged_count": len(queue),
            "safety_overrides_triggered": overrides_count,
            "sla_breaches_detected": sla_breaches_count,
            "missing_data_warnings_count": missing_data_warnings_count,
            "genuine_hazard_preserved_under_attack": genuine_preserved,
            "highest_priority_incidents": highest_priority_incidents,
            "department_assignments": department_assignments,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
