import os
import html
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

class ReportService:
    def generate_compliance_pdf(self, doc_data: dict, clauses: list, audits: list, output_path: str):
        doc = SimpleDocTemplate(output_path, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
        story = []
        styles = getSampleStyleSheet()

        # Custom Styles
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontSize=20,
            textColor=colors.HexColor('#1e293b'),
            spaceAfter=6
        )
        subtitle_style = ParagraphStyle(
            'SubtitleStyle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#64748b'),
            spaceAfter=20
        )
        section_heading = ParagraphStyle(
            'SectionHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#0f172a'),
            spaceBefore=15,
            spaceAfter=10
        )

        # Header Section
        story.append(Paragraph("Tata AI Legal Intelligence", title_style))
        story.append(Paragraph(f"Executive Compliance & Risk Assessment Report | Job ID: {html.escape(str(doc_data.get('job_id', 'N/A')))}", subtitle_style))
        story.append(Spacer(1, 10))

        # Document Summary Table
        safe_filename = html.escape(str(doc_data.get('filename', 'Unknown')))
        safe_business_unit = html.escape(str(doc_data.get('business_unit', 'Enterprise')))
        safe_confidence = html.escape(str(doc_data.get('ocr_confidence', 100.0)))
        safe_pages = html.escape(str(doc_data.get('pages', 1)))

        summary_data = [
            [Paragraph("<b>Filename:</b>", styles['Normal']), Paragraph(safe_filename, styles['Normal'])],
            [Paragraph("<b>Business Unit:</b>", styles['Normal']), Paragraph(safe_business_unit, styles['Normal'])],
            [Paragraph("<b>OCR Confidence:</b>", styles['Normal']), Paragraph(f"{safe_confidence}%", styles['Normal'])],
            [Paragraph("<b>Pages Processed:</b>", styles['Normal']), Paragraph(safe_pages, styles['Normal'])],
        ]
        summary_table = Table(summary_data, colWidths=[120, 400])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e1')),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
            ('PADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 15))

        # Extracted Clauses & Risk Matrix Section
        story.append(Paragraph("Extracted Clauses & Risk Matrix", section_heading))
        
        for idx, clause in enumerate(clauses, 1):
            if not clause:
                continue
            risk_level = str(clause.get('risk_level', 'LOW')).upper()
            risk_color = (
                colors.HexColor('#991b1b') if risk_level == 'HIGH' else
                colors.HexColor('#92400e') if risk_level == 'MEDIUM' else
                colors.HexColor('#065f46')
            )
            
            safe_type = html.escape(str(clause.get('clause_type', 'General Provision')))
            safe_risk = html.escape(risk_level)
            safe_text = html.escape(str(clause.get('extracted_text', '')))
            safe_rationale = html.escape(str(clause.get('risk_rationale', 'N/A')))

            clause_box_data = [
                [Paragraph(f"<b>#{idx}: {safe_type}</b>", styles['Normal']), Paragraph(f"<b>Risk: {safe_risk}</b>", ParagraphStyle('Risk', parent=styles['Normal'], textColor=risk_color))],
                [Paragraph(f"<b>Text:</b> {safe_text}", styles['Normal']), ""],
                [Paragraph(f"<b>Rationale:</b> {safe_rationale}", styles['Normal']), ""]
            ]
            clause_table = Table(clause_box_data, colWidths=[400, 120])
            clause_table.setStyle(TableStyle([
                ('SPAN', (0,1), (1,1)),
                ('SPAN', (0,2), (1,2)),
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#ffffff')),
                ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#e2e8f0')),
                ('PADDING', (0,0), (-1,-1), 8),
                ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ]))
            story.append(clause_table)
            story.append(Spacer(1, 10))

        # Human Governance & Audit Sign-Offs Section
        story.append(Spacer(1, 15))
        story.append(Paragraph("Human Governance & Audit Sign-Offs", section_heading))

        if audits:
            audit_headers = [
                [Paragraph("<b>Reviewer Identity</b>", styles['Normal']), Paragraph("<b>Governance Action</b>", styles['Normal'])]
            ]
            audit_data = []
            
            for audit in audits:
                if not audit:
                    continue
                action_str = str(audit.get('action', 'ACCEPT')).upper()
                action_color = colors.HexColor('#065f46') if action_str in ['ACCEPT', 'APPROVE'] else colors.HexColor('#991b1b')
                action_p = Paragraph(f"<b>{html.escape(action_str)}</b>", ParagraphStyle('Action', parent=styles['Normal'], textColor=action_color))
                reviewer_str = html.escape(str(audit.get('reviewer', 'reviewer@tata.com')))
                
                audit_data.append([
                    Paragraph(reviewer_str, styles['Normal']), 
                    action_p
                ])
            
            audit_table = Table(audit_headers + audit_data, colWidths=[260, 260])
            audit_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f1f5f9')),
                ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e1')),
                ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
                ('PADDING', (0,0), (-1,-1), 6),
            ]))
            story.append(audit_table)
        else:
            story.append(Paragraph("<i>No human review actions have been recorded for this document yet.</i>", styles['Normal']))

        # Build PDF
        doc.build(story)
        return output_path