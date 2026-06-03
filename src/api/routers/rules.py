from fastapi import APIRouter, HTTPException, Depends
from src.models.alert import AlertRuleCreate, AlertRuleUpdate, AlertRuleResponse
from src.db.postgres import (
    create_alert_rule, get_alert_rules, get_alert_rule,
    update_alert_rule, delete_alert_rule
)
from src.api.dependencies import require_permission

router = APIRouter(prefix="/alert_rules", tags=["alert_rules"])


@router.post("", response_model=AlertRuleResponse, dependencies=[Depends(require_permission("rules:create"))])
async def create_rule(rule: AlertRuleCreate):
    try:
        return create_alert_rule(
            rule.service_name,
            rule.metric_type,
            rule.threshold,
            rule.enabled
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", dependencies=[Depends(require_permission("rules:read"))])
async def list_rules(enabled_only: bool = False):
    try:
        rules = get_alert_rules(enabled_only)
        return {
            "rules": [
                {
                    "rule_id": r[0],
                    "service_name": r[1],
                    "metric_type": r[2],
                    "threshold": r[3],
                    "enabled": r[4],
                    "created_at": r[5].isoformat() if r[5] else None,
                    "updated_at": r[6].isoformat() if r[6] else None
                }
                for r in rules
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{rule_id}", response_model=AlertRuleResponse, dependencies=[Depends(require_permission("rules:read"))])
async def get_rule(rule_id: int):
    try:
        rule = get_alert_rule(rule_id)
        if not rule:
            raise HTTPException(status_code=404, detail="Alert rule not found")
        return rule
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{rule_id}", response_model=AlertRuleResponse, dependencies=[Depends(require_permission("rules:update"))])
async def update_rule(rule_id: int, updates: AlertRuleUpdate):
    try:
        rule = update_alert_rule(
            rule_id,
            updates.threshold,
            updates.enabled
        )
        if not rule:
            raise HTTPException(status_code=404, detail="Alert rule not found")
        return rule
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{rule_id}", dependencies=[Depends(require_permission("rules:delete"))])
async def delete_rule(rule_id: int):
    try:
        if not delete_alert_rule(rule_id):
            raise HTTPException(status_code=404, detail="Alert rule not found")
        return {"deleted": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
