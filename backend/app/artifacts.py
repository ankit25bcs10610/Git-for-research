import uuid

from app.db.models import Artifact


def create_artifact(session, workspace_id: str, artifact_type: str, name: str) -> str:
    artifact_id = str(uuid.uuid4())
    artifact = Artifact(
        id=artifact_id,
        workspace_id=workspace_id,
        type=artifact_type,
        name=name,
    )
    session.add(artifact)
    session.commit()
    return artifact_id


def get_artifact(session, artifact_id: str) -> Artifact:
    artifact = session.get(Artifact, artifact_id)
    if artifact is None:
        raise ValueError(f"artifact not found for id {artifact_id}")
    return artifact


def list_artifacts(session, workspace_id: str) -> list[Artifact]:
    return session.query(Artifact).filter_by(workspace_id=workspace_id).all()
