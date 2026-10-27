"""P0-028: dynamic agent-pivot query must be screened before provider."""
import asyncio
import pytest
from fastapi import HTTPException
from app.agent import execute_provider

def test_028_dynamic_agent_step_cannot_forward_private_tracking():
    case={'id':'synthetic','query':'Example Person','subject_type':'person'}
    job={'id':'synthetic','allow_web':1}
    choice={'provider':'brave_web','query':'Track this person live location'}
    with pytest.raises(HTTPException) as exc:
        asyncio.run(execute_provider(case,job,choice,'test-admin',1))
    assert exc.value.status_code==422
