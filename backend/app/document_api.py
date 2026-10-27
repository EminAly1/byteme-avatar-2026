"""Authenticated transient document views. POST returns bytes, never a posting."""
from uuid import UUID

from fastapi import APIRouter, Depends, Response

from app.api import authenticate, DB
from app import document_drafts as drafts
from app.document_pdf import render_pdf

router = APIRouter(prefix='/v1/document-drafts', dependencies=[Depends(authenticate)], tags=['document drafts'])
NO_STORE = {'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'}


@router.get('/sales/{sale_id}')
def document_source(sale_id: UUID, db: DB, response: Response):
    response.headers.update(NO_STORE)
    return drafts.source(db, sale_id)


@router.post('/proforma/pdf')
def document_pdf(body: drafts.PdfRequest, db: DB):
    data = drafts.source(db, body.sale_id)
    drafts.assert_fresh(data, body.expected_source_fingerprint)
    content = render_pdf(data, body.kind, body.draft)
    filename = f'{body.kind}-{body.sale_id}.pdf'  # validated UUID, never user title/reference
    return Response(content, media_type='application/pdf', headers={**NO_STORE,
        'Content-Disposition': f'attachment; filename="{filename}"'})
