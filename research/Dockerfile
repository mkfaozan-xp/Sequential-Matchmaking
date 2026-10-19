ARG PYTHON_BASE=python:3.12.14-slim
FROM ${PYTHON_BASE}
ARG POLICY_MODE=conservative
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 BLACKBOX_POLICY_MODE=${POLICY_MODE}
WORKDIR /app
COPY policy.py /app/policy.py
COPY blackbox/__init__.py blackbox/domain.py blackbox/features.py blackbox/outcome_history.py blackbox/ranking.py blackbox/compatibility.py blackbox/model.py blackbox/basis.py blackbox/allocation.py blackbox/clarification.py blackbox/contracts.py blackbox/policy.py blackbox/solve.py blackbox/registry.py blackbox/storage.py /app/blackbox/
COPY artifacts/deployment.json /app/artifacts/deployment.json
COPY --chown=65534:65534 artifacts/releases/ /app/artifacts/releases/
COPY starter/LICENSE starter/DATA_LICENSE.md /app/licenses/
USER 65534:65534
ENTRYPOINT ["python", "-B", "/app/policy.py"]
