# Tests

Not yet built — part of stage 2. Will unit-test `extract.py` / `retrieve.py` /
`analyze.py` with the Foundry and Azure AI Search clients mocked, so the pipeline
logic (chunking, citation assembly, the pydantic schemas) is verified without any
live Azure call or cost. Live-integration testing happens manually after real
deployment (stage 6).
