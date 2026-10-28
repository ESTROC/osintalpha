"""Single authenticated case initial-response bundle.

Reduces network round trips without altering substantive source evidence gates.
Existing specialist endpoints remain usable for lazy refreshed tabs.
"""
from __future__ import annotations
from typing import Literal
from fastapi import APIRouter,Depends
from . import main as core
router=APIRouter()

@router.get('/api/cases/{case_id}/initial-view')
def initial_view(case_id:str,depth:Literal['quick','standard','thorough']='standard',
                 actor=Depends(core.actor_from_cookie)):
    from . import v4,v5,query_diagnostics,decision_readiness,resumable_search
    from . import case_dossier,provider_ops,reviewed_report,candidate_refinement
    from . import db
    with db.connect() as conn:
        core.case_or_404(conn,case_id,actor)
    return {
       'triage':core.case_triage(case_id,actor=actor),
       'conversations':core.conversations(case_id,actor=actor),
       'researchPlan':v4.research_plan(case_id,depth=depth,actor=actor),
       'runs':v4.research_history(case_id,actor=actor),
       'intelligence':v4.intelligence(case_id,actor=actor),
       'webProviders':v5.providers(actor=actor),
       'candidates':v4.candidates(case_id,actor=actor),
       'queryExplain':query_diagnostics.explain_case(case_id,actor=actor),
       'readiness':decision_readiness.decision_readiness(case_id,actor=actor),
       'searchProgress':resumable_search.search_progress(case_id,actor=actor),
       'dossier':case_dossier.dossier(case_id,sort='relevance',status='all',
                    source_class='all',limit=35,actor=actor),
       'budget':provider_ops.case_budget(case_id,actor=actor),
       'draft':reviewed_report.preview_reviewed_draft(case_id,actor=actor),
       'refinements':candidate_refinement.list_refinements(case_id,actor=actor),
       'sourceTruthVerified':False,
       'initialRoundTripCount':1,
       'notice':'Aggregated response is scoped to authorized case. Other specialist modules remain available by lazy tab activation.'}
