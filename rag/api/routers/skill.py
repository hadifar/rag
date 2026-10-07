import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, UploadFile

from rag.api.deps import AuthenticatedUserDep, SkillServiceDep, get_current_user
from rag.api.schema.skill import SkillResponse

router = APIRouter(
    prefix="/api/skills", tags=["skills"], dependencies=[Depends(get_current_user)]
)


async def _read_skill_file(file: UploadFile, skill_service: SkillServiceDep) -> bytes:
    """The upload's content. One byte over the limit is enough for the service to
    reject it, without ever holding an oversized one in memory.
    """
    return await file.read(skill_service.max_bytes + 1)


@router.get("")
async def list_skills(
    current_user: AuthenticatedUserDep, skill_service: SkillServiceDep
) -> list[SkillResponse]:
    """The caller's skills, by name."""
    skills = await skill_service.list_for_user(current_user.id)
    return [SkillResponse.model_validate(s) for s in skills]


@router.post("", status_code=201)
async def upload_skill(
    data: Annotated[bytes, Depends(_read_skill_file)],
    current_user: AuthenticatedUserDep,
    skill_service: SkillServiceDep,
) -> SkillResponse:
    """Saves a SKILL.md file (frontmatter with `name` and `description`, then the
    instructions), replacing the caller's skill of that name if they have one.
    """
    skill = await skill_service.upload(current_user.id, data)
    return SkillResponse.model_validate(skill)


@router.delete("/{skill_id}", status_code=204)
async def delete_skill(
    skill_id: uuid.UUID,
    current_user: AuthenticatedUserDep,
    skill_service: SkillServiceDep,
) -> None:
    await skill_service.delete(current_user.id, skill_id)
