import uuid

from fastapi import APIRouter, Depends

from rag.api.deps import AuthenticatedUserDep, SkillServiceDep, get_current_user
from rag.api.schema.skill import SkillResponse
from rag.api.uploads import SkillUpload

router = APIRouter(
    prefix="/api/skills", tags=["skills"], dependencies=[Depends(get_current_user)]
)


@router.get("")
async def list_skills(
    current_user: AuthenticatedUserDep, skill_service: SkillServiceDep
) -> list[SkillResponse]:
    """The caller's skills, by name."""
    skills = await skill_service.list_for_user(current_user.id)
    return [SkillResponse.model_validate(s) for s in skills]


@router.post("", status_code=201)
async def upload_skill(
    upload: SkillUpload,
    current_user: AuthenticatedUserDep,
    skill_service: SkillServiceDep,
) -> SkillResponse:
    """Saves a SKILL.md file (frontmatter with `name` and `description`, then the
    instructions), or a .zip or .skill archive of one with its reference files,
    replacing the caller's skill of that name if they have one.
    """
    skill = await skill_service.upload(current_user.id, upload.data)
    return SkillResponse.model_validate(skill)


@router.delete("/{skill_id}", status_code=204)
async def delete_skill(
    skill_id: uuid.UUID,
    current_user: AuthenticatedUserDep,
    skill_service: SkillServiceDep,
) -> None:
    await skill_service.delete(current_user.id, skill_id)
