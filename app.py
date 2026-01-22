"""Flask web application for DCS Interconnection Diagram Generator."""

import os
from flask import Flask, render_template, request, send_file, jsonify, flash, redirect, url_for
from werkzeug.utils import secure_filename
from pathlib import Path

from src.parsers import load_io_list, filter_instruments_by_area, group_instruments_by_area
from src.engine import (
    classify_jb_type, TagGenerator, suggest_jb_count, calculate_jb_allocation_plan,
    get_signal_type_summary, separate_instruments_by_signal_type, allocate_by_signal_type,
    ANALOG_SIGNAL_TYPES, DIGITAL_SIGNAL_TYPES
)
from src.drawing import render_interconnection_diagram, render_multi_jb_diagram
import zipfile

app = Flask(__name__)
app.secret_key = 'dcs-diagram-generator-secret-key'

# Configuration
UPLOAD_FOLDER = Path('uploads')
OUTPUT_FOLDER = Path('examples/output')
ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'pdf'}

UPLOAD_FOLDER.mkdir(exist_ok=True)
OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    """Home page with upload form."""
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and parse I/O list."""
    if 'file' not in request.files:
        flash('No file selected', 'error')
        return redirect(url_for('index'))

    file = request.files['file']

    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('index'))

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = UPLOAD_FOLDER / filename
        file.save(filepath)

        # Parse the I/O list
        try:
            result = load_io_list(str(filepath))

            if not result.is_valid:
                errors = [e.message for e in result.validation_result.errors]
                flash(f'Validation errors: {", ".join(errors)}', 'error')
                return redirect(url_for('index'))

            # Group by area
            groups = group_instruments_by_area(result.instruments)
            areas = {area: len(insts) for area, insts in groups.items()}

            # Get JB suggestions
            suggestions = suggest_jb_count(result.instruments)

            # Get signal type summary (Analog vs Digital breakdown)
            signal_summary = get_signal_type_summary(result.instruments)

            # Calculate JB allocation plan for each signal type
            analog_plan = None
            digital_plan = None

            if signal_summary['analog_count'] > 0:
                analog_plan = calculate_jb_allocation_plan(signal_summary['analog_count'])
            if signal_summary['digital_count'] > 0:
                digital_plan = calculate_jb_allocation_plan(signal_summary['digital_count'])

            allocation_info = {
                'analog': {
                    'count': signal_summary['analog_count'],
                    'types': list(signal_summary['analog_types'].keys()),
                    'jb_size': analog_plan.jb_size.value if analog_plan else 0,
                    'jb_size_name': analog_plan.jb_size.name if analog_plan else 'N/A',
                    'num_jbs': analog_plan.num_jbs_needed if analog_plan else 0,
                    'instruments_per_jb': analog_plan.instruments_per_jb if analog_plan else [],
                    'effective_capacity': analog_plan.jb_capacity if analog_plan else 0,
                } if signal_summary['analog_count'] > 0 else None,
                'digital': {
                    'count': signal_summary['digital_count'],
                    'types': list(signal_summary['digital_types'].keys()),
                    'jb_size': digital_plan.jb_size.value if digital_plan else 0,
                    'jb_size_name': digital_plan.jb_size.name if digital_plan else 'N/A',
                    'num_jbs': digital_plan.num_jbs_needed if digital_plan else 0,
                    'instruments_per_jb': digital_plan.instruments_per_jb if digital_plan else [],
                    'effective_capacity': digital_plan.jb_capacity if digital_plan else 0,
                } if signal_summary['digital_count'] > 0 else None,
            }

            return render_template(
                'configure.html',
                filename=filename,
                total_instruments=len(result.instruments),
                areas=areas,
                suggestions=suggestions,
                allocation_info=allocation_info,
                signal_summary=signal_summary
            )

        except Exception as e:
            flash(f'Error parsing file: {str(e)}', 'error')
            return redirect(url_for('index'))

    flash('Invalid file type. Please upload an Excel file (.xlsx or .xls)', 'error')
    return redirect(url_for('index'))


@app.route('/generate', methods=['POST'])
def generate_diagram():
    """Generate the interconnection diagram with signal type segregation."""
    try:
        filename = request.form.get('filename')
        area = request.form.get('area', 'all')
        drawing_number = request.form.get('drawing_number', 'DWG-001')

        # Get separate Analog and Digital JB tags
        analog_jb_tag = request.form.get('analog_jb_tag')
        analog_cabinet_tag = request.form.get('analog_cabinet_tag')
        digital_jb_tag = request.form.get('digital_jb_tag')
        digital_cabinet_tag = request.form.get('digital_cabinet_tag')

        # Fallback to legacy single JB tag if separate tags not provided
        legacy_jb_tag = request.form.get('jb_tag')
        legacy_cabinet_tag = request.form.get('cabinet_tag')

        if not filename:
            flash('Please fill in all required fields', 'error')
            return redirect(url_for('index'))

        # Load I/O list
        filepath = UPLOAD_FOLDER / filename
        result = load_io_list(str(filepath))

        # Filter by area if specified
        if area and area.lower() != 'all':
            instruments = filter_instruments_by_area(result.instruments, area)
        else:
            instruments = result.instruments

        if not instruments:
            flash('No instruments found for the selected area', 'error')
            return redirect(url_for('index'))

        # Separate instruments by signal type
        separated = separate_instruments_by_signal_type(instruments)
        analog_instruments = separated.get('analog', [])
        digital_instruments = separated.get('digital', [])

        output_files = []
        jb_tags_generated = []
        tag_gen = TagGenerator()

        # Generate Analog JB diagrams if we have analog instruments and tags
        if analog_instruments and analog_jb_tag and analog_cabinet_tag:
            analog_multipair_tag = tag_gen.generate_multipair_cable_tag()
            analog_tb_tag = tag_gen.generate_terminal_block_tag(analog_multipair_tag)
            analog_title = f"{analog_jb_tag} (ANALOG JB)"
            analog_output = OUTPUT_FOLDER / f"{analog_jb_tag.replace('/', '_')}.pdf"

            analog_result = render_multi_jb_diagram(
                instruments=analog_instruments,
                base_jb_tag=analog_jb_tag,
                cabinet_tag=analog_cabinet_tag,
                base_multipair_cable_tag=analog_multipair_tag,
                base_tb_tag=analog_tb_tag,
                output_path=str(analog_output),
                drawing_number=drawing_number,
                title=analog_title,
                signal_category="ANALOG"
            )
            output_files.extend(analog_result['output_files'])
            jb_tags_generated.extend(analog_result['jb_tags'])

        # Generate Digital JB diagrams if we have digital instruments and tags
        if digital_instruments and digital_jb_tag and digital_cabinet_tag:
            digital_multipair_tag = tag_gen.generate_multipair_cable_tag()
            digital_tb_tag = tag_gen.generate_terminal_block_tag(digital_multipair_tag)
            digital_title = f"{digital_jb_tag} (DIGITAL JB)"
            digital_output = OUTPUT_FOLDER / f"{digital_jb_tag.replace('/', '_')}.pdf"

            digital_result = render_multi_jb_diagram(
                instruments=digital_instruments,
                base_jb_tag=digital_jb_tag,
                cabinet_tag=digital_cabinet_tag,
                base_multipair_cable_tag=digital_multipair_tag,
                base_tb_tag=digital_tb_tag,
                output_path=str(digital_output),
                drawing_number=drawing_number,
                title=digital_title,
                signal_category="DIGITAL"
            )
            output_files.extend(digital_result['output_files'])
            jb_tags_generated.extend(digital_result['jb_tags'])

        # Fallback to legacy mode if no separate tags provided
        if not output_files and legacy_jb_tag and legacy_cabinet_tag:
            jb_type = classify_jb_type(instruments)
            multipair_cable_tag = tag_gen.generate_multipair_cable_tag()
            tb_tag = tag_gen.generate_terminal_block_tag(multipair_cable_tag)
            title = f"{legacy_jb_tag} ({jb_type.value} JB)"
            output_path = OUTPUT_FOLDER / f"{legacy_jb_tag.replace('/', '_')}.pdf"

            render_result = render_multi_jb_diagram(
                instruments=instruments,
                base_jb_tag=legacy_jb_tag,
                cabinet_tag=legacy_cabinet_tag,
                base_multipair_cable_tag=multipair_cable_tag,
                base_tb_tag=tb_tag,
                output_path=str(output_path),
                drawing_number=drawing_number,
                title=title,
            )
            output_files = render_result['output_files']
            jb_tags_generated = render_result['jb_tags']

        if not output_files:
            flash('No diagrams generated. Please provide JB tags.', 'error')
            return redirect(url_for('index'))

        # If multiple files, create a zip
        if len(output_files) > 1:
            zip_filename = f"JB_diagrams_{filename.replace('.xlsx', '').replace('.xls', '')}.zip"
            zip_path = OUTPUT_FOLDER / zip_filename
            with zipfile.ZipFile(zip_path, 'w') as zf:
                for pdf_file in output_files:
                    zf.write(pdf_file, Path(pdf_file).name)

            flash(f'Generated {len(jb_tags_generated)} JB diagrams: {", ".join(jb_tags_generated)}', 'success')
            return send_file(
                zip_path,
                as_attachment=True,
                download_name=zip_filename,
                mimetype='application/zip'
            )
        else:
            # Single file - return directly
            return send_file(
                output_files[0],
                as_attachment=True,
                download_name=Path(output_files[0]).name,
                mimetype='application/pdf'
            )

    except Exception as e:
        flash(f'Error generating diagram: {str(e)}', 'error')
        return redirect(url_for('index'))


@app.route('/api/parse', methods=['POST'])
def api_parse():
    """API endpoint to parse an I/O list."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']

    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file'}), 400

    filename = secure_filename(file.filename)
    filepath = UPLOAD_FOLDER / filename
    file.save(filepath)

    try:
        result = load_io_list(str(filepath))

        if not result.is_valid:
            return jsonify({
                'valid': False,
                'errors': [e.message for e in result.validation_result.errors]
            }), 400

        groups = group_instruments_by_area(result.instruments)

        return jsonify({
            'valid': True,
            'filename': filename,
            'total_instruments': len(result.instruments),
            'areas': {area: len(insts) for area, insts in groups.items()},
            'suggestions': suggest_jb_count(result.instruments)
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/generate', methods=['POST'])
def api_generate():
    """API endpoint to generate a diagram."""
    data = request.json

    required_fields = ['filename', 'jb_tag', 'cabinet_tag']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400

    try:
        filepath = UPLOAD_FOLDER / data['filename']
        result = load_io_list(str(filepath))

        area = data.get('area', 'all')
        if area and area.lower() != 'all':
            instruments = filter_instruments_by_area(result.instruments, area)
        else:
            instruments = result.instruments

        if not instruments:
            return jsonify({'error': 'No instruments found'}), 400

        jb_type = classify_jb_type(instruments)
        tag_gen = TagGenerator()
        multipair_cable_tag = tag_gen.generate_multipair_cable_tag()
        tb_tag = tag_gen.generate_terminal_block_tag(multipair_cable_tag)

        title = f"{data['jb_tag']} ({jb_type.value} JB)"
        output_filename = f"{data['jb_tag'].replace('/', '_')}.pdf"
        output_path = OUTPUT_FOLDER / output_filename

        render_interconnection_diagram(
            instruments=instruments,
            jb_tag=data['jb_tag'],
            cabinet_tag=data['cabinet_tag'],
            multipair_cable_tag=multipair_cable_tag,
            tb_tag=tb_tag,
            output_path=str(output_path),
            drawing_number=data.get('drawing_number', 'DWG-001'),
            title=title,
        )

        return jsonify({
            'success': True,
            'download_url': f'/download/{output_filename}',
            'jb_type': jb_type.value,
            'instrument_count': len(instruments),
            'multipair_cable': multipair_cable_tag,
            'tb_tag': tb_tag
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/download/<filename>')
def download_file(filename):
    """Download a generated PDF."""
    filepath = OUTPUT_FOLDER / secure_filename(filename)
    if filepath.exists():
        return send_file(filepath, as_attachment=True)
    return jsonify({'error': 'File not found'}), 404


# ============== PDF Extraction Routes ==============

# Store for extracted instruments (in production, use session or database)
extracted_instruments_store = {}


@app.route('/upload-pdf', methods=['POST'])
def upload_pdf():
    """Handle PDF upload for extraction."""
    if 'file' not in request.files:
        flash('No file selected', 'error')
        return redirect(url_for('index'))

    file = request.files['file']

    if file.filename == '' or not file.filename.lower().endswith('.pdf'):
        flash('Please upload a PDF file', 'error')
        return redirect(url_for('index'))

    filename = secure_filename(file.filename)
    filepath = UPLOAD_FOLDER / filename
    file.save(filepath)

    try:
        from src.parsers import PDF_EXTRACTION_AVAILABLE
        if not PDF_EXTRACTION_AVAILABLE:
            flash('PDF extraction is not available. Please install: pip install pdf2image pytesseract', 'error')
            return redirect(url_for('index'))

        from pdf2image import pdfinfo_from_path
        info = pdfinfo_from_path(str(filepath))
        total_pages = info.get('Pages', 1)

        return render_template(
            'pdf_extract.html',
            filename=filename,
            page=1,
            total_pages=total_pages
        )

    except Exception as e:
        flash(f'Error processing PDF: {str(e)}', 'error')
        return redirect(url_for('index'))


@app.route('/pdf-page/<filename>/<int:page>')
def get_pdf_page(filename, page):
    """Get a specific page of a PDF as an image."""
    try:
        from src.parsers import get_pdf_page_as_image
        import io

        filepath = UPLOAD_FOLDER / secure_filename(filename)
        if not filepath.exists():
            return jsonify({'error': 'File not found'}), 404

        img = get_pdf_page_as_image(str(filepath), page=page, dpi=150)

        if img is None:
            return jsonify({'error': 'Could not render page'}), 500

        # Convert to bytes
        img_io = io.BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)

        return send_file(img_io, mimetype='image/png')

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/pdf-extract', methods=['POST'])
def api_pdf_extract():
    """API endpoint to extract instruments from PDF."""
    try:
        from src.parsers import PDF_EXTRACTION_AVAILABLE
        if not PDF_EXTRACTION_AVAILABLE:
            return jsonify({'error': 'PDF extraction not available'}), 400

        from src.parsers import PDFExtractor

        data = request.json
        filename = data.get('filename')
        page = data.get('page', 1)
        region = data.get('region')  # {left, top, right, bottom} or None

        filepath = UPLOAD_FOLDER / secure_filename(filename)
        if not filepath.exists():
            return jsonify({'error': 'File not found'}), 404

        extractor = PDFExtractor()

        if region:
            # Extract from specific region
            region_tuple = (
                int(region['left']),
                int(region['top']),
                int(region['right']),
                int(region['bottom'])
            )
            result = extractor.extract_from_region(str(filepath), page, region_tuple)
        else:
            # Extract from full page
            from pdf2image import convert_from_path
            images = convert_from_path(str(filepath), dpi=300, first_page=page, last_page=page)
            result = extractor._process_images(images)

        return jsonify({
            'instruments': [
                {
                    'tag_number': inst.tag_number,
                    'instrument_type': inst.instrument_type,
                    'confidence': inst.confidence,
                    'area': inst.area,
                    'service': inst.service,
                    'source_text': inst.source_text
                }
                for inst in result.instruments
            ],
            'raw_text': result.raw_text,
            'warnings': result.warnings
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/store-extracted', methods=['POST'])
def store_extracted():
    """Store extracted instruments for later use."""
    data = request.json
    instruments = data.get('instruments', [])

    # Generate a simple session ID
    import uuid
    session_id = str(uuid.uuid4())[:8]
    extracted_instruments_store[session_id] = instruments

    return jsonify({'success': True, 'session_id': session_id})


@app.route('/configure-extracted')
def configure_extracted():
    """Configure diagram from extracted instruments."""
    # Get the most recent extraction
    if not extracted_instruments_store:
        flash('No extracted instruments found. Please extract from PDF first.', 'error')
        return redirect(url_for('index'))

    session_id = list(extracted_instruments_store.keys())[-1]
    instruments_data = extracted_instruments_store[session_id]

    if not instruments_data:
        flash('No instruments found', 'error')
        return redirect(url_for('index'))

    # Convert to Instrument objects for proper signal type detection
    from src.models import Instrument
    instruments = [
        Instrument(
            tag_number=i.get('tag_number', ''),
            instrument_type=i.get('instrument_type', ''),
            service=i.get('service', 'Extracted from PDF'),
            area=i.get('area', '000')
        )
        for i in instruments_data
    ]

    # Group by area
    areas = {}
    for inst in instruments_data:
        area = inst.get('area', '000')
        if area not in areas:
            areas[area] = 0
        areas[area] += 1

    # Get proper signal type summary using the engine function
    signal_summary = get_signal_type_summary(instruments)

    # Calculate JB allocation plan for each signal type
    analog_plan = None
    digital_plan = None

    if signal_summary['analog_count'] > 0:
        analog_plan = calculate_jb_allocation_plan(signal_summary['analog_count'])
    if signal_summary['digital_count'] > 0:
        digital_plan = calculate_jb_allocation_plan(signal_summary['digital_count'])

    suggestions = {
        'analog_jbs': analog_plan.num_jbs_needed if analog_plan else 0,
        'digital_jbs': digital_plan.num_jbs_needed if digital_plan else 0,
        'analog_instruments': signal_summary['analog_count'],
        'digital_instruments': signal_summary['digital_count']
    }

    allocation_info = {
        'analog': {
            'count': signal_summary['analog_count'],
            'types': list(signal_summary['analog_types'].keys()),
            'jb_size': analog_plan.jb_size.value if analog_plan else 0,
            'jb_size_name': analog_plan.jb_size.name if analog_plan else 'N/A',
            'num_jbs': analog_plan.num_jbs_needed if analog_plan else 0,
            'instruments_per_jb': analog_plan.instruments_per_jb if analog_plan else [],
            'effective_capacity': analog_plan.jb_capacity if analog_plan else 0,
        } if signal_summary['analog_count'] > 0 else None,
        'digital': {
            'count': signal_summary['digital_count'],
            'types': list(signal_summary['digital_types'].keys()),
            'jb_size': digital_plan.jb_size.value if digital_plan else 0,
            'jb_size_name': digital_plan.jb_size.name if digital_plan else 'N/A',
            'num_jbs': digital_plan.num_jbs_needed if digital_plan else 0,
            'instruments_per_jb': digital_plan.instruments_per_jb if digital_plan else [],
            'effective_capacity': digital_plan.jb_capacity if digital_plan else 0,
        } if signal_summary['digital_count'] > 0 else None,
    }

    return render_template(
        'configure.html',
        filename=f'extracted_{session_id}',
        total_instruments=len(instruments_data),
        areas=areas,
        suggestions=suggestions,
        allocation_info=allocation_info,
        signal_summary=signal_summary,
        from_pdf=True
    )


@app.route('/generate-from-extracted', methods=['POST'])
def generate_from_extracted():
    """Generate diagram from extracted instruments with signal type segregation."""
    try:
        session_id = request.form.get('filename', '').replace('extracted_', '')
        instruments_data = extracted_instruments_store.get(session_id, [])

        if not instruments_data:
            flash('No extracted instruments found', 'error')
            return redirect(url_for('index'))

        # Convert to Instrument objects
        from src.models import Instrument
        instruments = [
            Instrument(
                tag_number=i.get('tag_number', ''),
                instrument_type=i.get('instrument_type', ''),
                service=i.get('service', 'Extracted from PDF'),
                area=i.get('area', '000')
            )
            for i in instruments_data
        ]

        area = request.form.get('area', 'all')
        if area and area.lower() != 'all':
            instruments = [i for i in instruments if i.area == area]

        drawing_number = request.form.get('drawing_number', 'DWG-001')

        # Get separate Analog and Digital JB tags
        analog_jb_tag = request.form.get('analog_jb_tag')
        analog_cabinet_tag = request.form.get('analog_cabinet_tag')
        digital_jb_tag = request.form.get('digital_jb_tag')
        digital_cabinet_tag = request.form.get('digital_cabinet_tag')

        # Fallback to legacy single JB tag if separate tags not provided
        legacy_jb_tag = request.form.get('jb_tag')
        legacy_cabinet_tag = request.form.get('cabinet_tag')

        # Separate instruments by signal type
        separated = separate_instruments_by_signal_type(instruments)
        analog_instruments = separated.get('analog', [])
        digital_instruments = separated.get('digital', [])

        output_files = []
        jb_tags_generated = []
        tag_gen = TagGenerator()

        # Generate Analog JB diagrams if we have analog instruments and tags
        if analog_instruments and analog_jb_tag and analog_cabinet_tag:
            analog_multipair_tag = tag_gen.generate_multipair_cable_tag()
            analog_tb_tag = tag_gen.generate_terminal_block_tag(analog_multipair_tag)
            analog_title = f"{analog_jb_tag} (ANALOG JB)"
            analog_output = OUTPUT_FOLDER / f"{analog_jb_tag.replace('/', '_')}.pdf"

            analog_result = render_multi_jb_diagram(
                instruments=analog_instruments,
                base_jb_tag=analog_jb_tag,
                cabinet_tag=analog_cabinet_tag,
                base_multipair_cable_tag=analog_multipair_tag,
                base_tb_tag=analog_tb_tag,
                output_path=str(analog_output),
                drawing_number=drawing_number,
                title=analog_title,
                signal_category="ANALOG"
            )
            output_files.extend(analog_result['output_files'])
            jb_tags_generated.extend(analog_result['jb_tags'])

        # Generate Digital JB diagrams if we have digital instruments and tags
        if digital_instruments and digital_jb_tag and digital_cabinet_tag:
            digital_multipair_tag = tag_gen.generate_multipair_cable_tag()
            digital_tb_tag = tag_gen.generate_terminal_block_tag(digital_multipair_tag)
            digital_title = f"{digital_jb_tag} (DIGITAL JB)"
            digital_output = OUTPUT_FOLDER / f"{digital_jb_tag.replace('/', '_')}.pdf"

            digital_result = render_multi_jb_diagram(
                instruments=digital_instruments,
                base_jb_tag=digital_jb_tag,
                cabinet_tag=digital_cabinet_tag,
                base_multipair_cable_tag=digital_multipair_tag,
                base_tb_tag=digital_tb_tag,
                output_path=str(digital_output),
                drawing_number=drawing_number,
                title=digital_title,
                signal_category="DIGITAL"
            )
            output_files.extend(digital_result['output_files'])
            jb_tags_generated.extend(digital_result['jb_tags'])

        # Fallback to legacy mode if no separate tags provided
        if not output_files and legacy_jb_tag and legacy_cabinet_tag:
            jb_type = classify_jb_type(instruments)
            multipair_cable_tag = tag_gen.generate_multipair_cable_tag()
            tb_tag = tag_gen.generate_terminal_block_tag(multipair_cable_tag)
            title = f"{legacy_jb_tag} ({jb_type.value} JB)"
            output_path = OUTPUT_FOLDER / f"{legacy_jb_tag.replace('/', '_')}.pdf"

            render_result = render_multi_jb_diagram(
                instruments=instruments,
                base_jb_tag=legacy_jb_tag,
                cabinet_tag=legacy_cabinet_tag,
                base_multipair_cable_tag=multipair_cable_tag,
                base_tb_tag=tb_tag,
                output_path=str(output_path),
                drawing_number=drawing_number,
                title=title,
            )
            output_files = render_result['output_files']
            jb_tags_generated = render_result['jb_tags']

        if not output_files:
            flash('No diagrams generated. Please provide JB tags.', 'error')
            return redirect(url_for('index'))

        # If multiple files, create a zip
        if len(output_files) > 1:
            zip_filename = f"JB_diagrams_extracted_{session_id}.zip"
            zip_path = OUTPUT_FOLDER / zip_filename
            with zipfile.ZipFile(zip_path, 'w') as zf:
                for pdf_file in output_files:
                    zf.write(pdf_file, Path(pdf_file).name)

            flash(f'Generated {len(jb_tags_generated)} JB diagrams: {", ".join(jb_tags_generated)}', 'success')
            return send_file(
                zip_path,
                as_attachment=True,
                download_name=zip_filename,
                mimetype='application/zip'
            )
        else:
            # Single file - return directly
            return send_file(
                output_files[0],
                as_attachment=True,
                download_name=Path(output_files[0]).name,
                mimetype='application/pdf'
            )

    except Exception as e:
        flash(f'Error generating diagram: {str(e)}', 'error')
        return redirect(url_for('index'))


# ============================================================================
# I/O CARD ALLOCATION ROUTES
# ============================================================================

# Store for allocation results (in-memory, per session)
io_allocation_store = {}


@app.route('/io-allocation')
def io_allocation_page():
    """I/O Card Allocation landing page."""
    return render_template('io_allocation_landing.html')


@app.route('/io-allocation/calculate', methods=['POST'])
def calculate_io_allocation_route():
    """Calculate I/O allocation from uploaded file with AI-powered custom rules."""
    from src.engine.io_allocator import IOAllocator
    from collections import defaultdict
    import uuid
    import math

    # Initialize variables for rule interpretation
    rules_applied = None
    rules_interpretation = None

    try:
        # Check for file
        if 'file' not in request.files:
            flash('No file selected', 'error')
            return redirect(url_for('io_allocation_page'))

        file = request.files['file']
        vendor = request.form.get('vendor', 'Yokogawa')
        custom_rules_text = request.form.get('custom_rules', '').strip()

        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(url_for('io_allocation_page'))

        if vendor != 'Yokogawa':
            flash(f'{vendor} coming soon. Currently only Yokogawa is supported.', 'warning')
            return redirect(url_for('io_allocation_page'))

        if not allowed_file(file.filename):
            flash('Invalid file type. Please upload an Excel (.xlsx, .xls) or PDF file', 'error')
            return redirect(url_for('io_allocation_page'))

        # Save file
        filename = secure_filename(file.filename)
        filepath = UPLOAD_FOLDER / filename
        file.save(filepath)

        # Determine file type and parse accordingly
        file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''

        if file_ext == 'pdf':
            # Extract instruments from PDF using OCR
            try:
                from src.parsers.pdf_extractor import PDFExtractor
                extractor = PDFExtractor()
                extraction_result = extractor.extract_from_file(str(filepath))

                if not extraction_result.instruments:
                    flash('No instruments found in the PDF. Make sure the PDF contains instrument tags.', 'error')
                    return redirect(url_for('io_allocation_page'))

                # Convert to Instrument objects
                instruments = extractor.to_instruments(extraction_result.instruments)

                if extraction_result.warnings:
                    for warning in extraction_result.warnings[:3]:  # Show first 3 warnings
                        flash(f'PDF extraction warning: {warning}', 'warning')

                # Create a simple result object for compatibility
                class PDFResult:
                    def __init__(self, instruments):
                        self.instruments = instruments
                        self.is_valid = True

                result = PDFResult(instruments)

            except ImportError:
                flash('PDF extraction requires additional packages. Install: pip install pdf2image pytesseract', 'error')
                return redirect(url_for('io_allocation_page'))
            except Exception as e:
                flash(f'Error extracting from PDF: {str(e)}', 'error')
                return redirect(url_for('io_allocation_page'))
        else:
            # Parse Excel I/O list
            result = load_io_list(str(filepath))

            if not result.is_valid:
                errors = [e.message for e in result.validation_result.errors]
                flash(f'Validation errors: {", ".join(errors)}', 'error')
                return redirect(url_for('io_allocation_page'))

        if not result.instruments:
            flash('No instruments found in the file', 'error')
            return redirect(url_for('io_allocation_page'))

        # Parse custom rules using LLM if provided
        spare_percent = 0.20  # Default
        if custom_rules_text:
            try:
                from src.services.llm_rules_service import LLMRulesService, AllocationRules
                import os
                api_key = os.environ.get('ANTHROPIC_API_KEY', '')
                if not api_key:
                    raise ValueError("ANTHROPIC_API_KEY environment variable not set")
                llm_service = LLMRulesService(api_key=api_key)
                rules_applied = llm_service.parse_rules(custom_rules_text)
                rules_interpretation = getattr(rules_applied, '_interpretation', '')

                # Apply parsed rules
                spare_percent = rules_applied.spare_percent
                flash(f'AI interpreted your rules: {rules_interpretation}', 'success')
            except Exception as e:
                flash(f'Could not parse custom rules (using defaults): {str(e)}', 'warning')
                rules_applied = None

        # Perform I/O allocation with custom rules
        allocator = IOAllocator(vendor=vendor, spare_percent=spare_percent)

        # Apply additional rules if parsed
        if rules_applied:
            allocator.custom_rules = rules_applied

        # Get system type from parse result if available
        system_type_override = getattr(result, 'system_type', None)
        if system_type_override:
            flash(f'Detected system type: {system_type_override}', 'info')

        allocation_result = allocator.allocate(result.instruments, system_type_override=system_type_override)

        # Store result
        session_id = str(uuid.uuid4())[:8]
        io_allocation_store[session_id] = {
            'result': allocation_result,
            'instruments': result.instruments,
            'filename': filename,
            'vendor': vendor,
            'rules_applied': rules_applied.to_dict() if rules_applied else None,
            'rules_interpretation': rules_interpretation
        }

        # Prepare template data
        def prepare_allocation_rows(summary, cards):
            rows = []
            cards_by_type = defaultdict(list)
            for card in cards:
                cards_by_type[card.module.io_type.value].append(card)

            for io_type in ['AI', 'AO', 'DI', 'DO']:
                signal_count = summary.get(io_type, 0)
                type_cards = cards_by_type.get(io_type, [])

                if signal_count > 0 or type_cards:
                    module_model = type_cards[0].module.model if type_cards else 'N/A'
                    channels_per_card = type_cards[0].total_channels if type_cards else 0
                    total_channels = sum(c.total_channels for c in type_cards)
                    spare = total_channels - signal_count if total_channels > 0 else 0
                    spare_pct = round((spare / total_channels) * 100, 1) if total_channels > 0 else 0

                    rows.append({
                        'io_type': io_type,
                        'signal_count': signal_count,
                        'channels_needed': math.ceil(signal_count * 1.2) if signal_count > 0 else 0,
                        'module_model': module_model,
                        'channels_per_card': channels_per_card,
                        'cards_required': len(type_cards),
                        'spare_percent': spare_pct
                    })
            return rows

        dcs_allocation = prepare_allocation_rows(allocation_result.dcs_summary, allocation_result.dcs_cards)
        sis_allocation = prepare_allocation_rows(allocation_result.sis_summary, allocation_result.sis_cards)
        rtu_allocation = prepare_allocation_rows(allocation_result.rtu_summary, allocation_result.rtu_cards)

        # Prepare detailed channel assignments
        def prepare_channel_details(cards):
            details = []
            for card in cards:
                channels = []
                for ch_num in sorted(card.channel_assignments.keys()):
                    ch_data = card.channel_assignments[ch_num]
                    channels.append({
                        'number': ch_num,
                        'tag': ch_data.get('tag', 'SPARE'),
                        'service': ch_data.get('service', ''),
                        'type': ch_data.get('type', ''),
                        'status': ch_data.get('status', 'SPARE')
                    })
                spare_pct = round((card.spare_channels / card.total_channels) * 100, 1) if card.total_channels > 0 else 0
                details.append({
                    'module': card.module.model,
                    'io_type': card.module.io_type.value,
                    'card_number': card.card_number,
                    'channels': channels,
                    'total': card.total_channels,
                    'used': card.used_channels,
                    'spare': card.spare_channels,
                    'spare_pct': spare_pct
                })
            return details

        channel_details = {
            'DCS': prepare_channel_details(allocation_result.dcs_cards),
            'SIS': prepare_channel_details(allocation_result.sis_cards),
            'RTU': prepare_channel_details(allocation_result.rtu_cards)
        }

        # Build custom rules display info
        custom_rules_info = None
        if rules_applied:
            custom_rules_info = {
                'interpretation': rules_interpretation,
                'spare_percent': rules_applied.spare_percent * 100,
                'rules': rules_applied.custom_rules,
                'segregate_by_area': rules_applied.segregate_by_area,
                'max_cabinets_per_area': rules_applied.max_cabinets_per_area,
                'group_by_loop': rules_applied.group_by_loop
            }

        return render_template(
            'io_allocation.html',
            session_id=session_id,
            vendor=vendor,
            total_instruments=len(result.instruments),
            total_cards=allocation_result.total_cards,
            segregation_count=len(allocation_result.segregation_rules_applied),
            dcs_allocation=dcs_allocation,
            sis_allocation=sis_allocation,
            rtu_allocation=rtu_allocation,
            channel_details=channel_details,
            custom_rules_info=custom_rules_info,
            segregation_rules=allocation_result.segregation_rules_applied
        )

    except Exception as e:
        flash(f'Error calculating allocation: {str(e)}', 'error')
        return redirect(url_for('io_allocation_page'))


@app.route('/api/io-allocation/export', methods=['POST'])
def export_io_allocation():
    """Export I/O allocation to Excel."""
    import pandas as pd
    from io import BytesIO

    data = request.json
    session_id = data.get('session_id')

    if session_id not in io_allocation_store:
        return jsonify({'error': 'Session not found'}), 404

    stored = io_allocation_store[session_id]
    result = stored['result']

    def create_cards_df(cards, system_name):
        if not cards:
            return pd.DataFrame()
        rows = []
        for card in cards:
            rows.append({
                'System': system_name,
                'Card #': card.card_number,
                'Module': card.module.model,
                'I/O Type': card.module.io_type.value,
                'Total Channels': card.total_channels,
                'Used': card.used_channels,
                'Spare': card.spare_channels,
                'Utilization %': f"{card.utilization_percent:.1f}%"
            })
        return pd.DataFrame(rows)

    def create_summary_df(result):
        rows = [
            {'System': 'DCS', **result.dcs_summary, 'Total Cards': len(result.dcs_cards)},
            {'System': 'SIS', **result.sis_summary, 'Total Cards': len(result.sis_cards)},
            {'System': 'RTU', **result.rtu_summary, 'Total Cards': len(result.rtu_cards)},
        ]
        return pd.DataFrame(rows)

    def create_channel_assignments_df(cards, system_name):
        """Create detailed channel assignment dataframe."""
        if not cards:
            return pd.DataFrame()
        rows = []
        for card in cards:
            for ch_num in sorted(card.channel_assignments.keys()):
                ch_data = card.channel_assignments[ch_num]
                rows.append({
                    'System': system_name,
                    'Card #': card.card_number,
                    'Module': card.module.model,
                    'I/O Type': card.module.io_type.value,
                    'Channel': ch_num,
                    'Instrument Tag': ch_data.get('tag', 'SPARE'),
                    'Instrument Type': ch_data.get('type', ''),
                    'Service': ch_data.get('service', ''),
                    'Status': ch_data.get('status', 'SPARE')
                })
        return pd.DataFrame(rows)

    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Summary sheet
        summary_df = create_summary_df(result)
        summary_df.to_excel(writer, sheet_name='Summary', index=False)

        # DCS cards
        dcs_df = create_cards_df(result.dcs_cards, 'DCS')
        if not dcs_df.empty:
            dcs_df.to_excel(writer, sheet_name='DCS Cards', index=False)

        # SIS cards
        sis_df = create_cards_df(result.sis_cards, 'SIS')
        if not sis_df.empty:
            sis_df.to_excel(writer, sheet_name='SIS Cards', index=False)

        # RTU cards
        rtu_df = create_cards_df(result.rtu_cards, 'RTU')
        if not rtu_df.empty:
            rtu_df.to_excel(writer, sheet_name='RTU Cards', index=False)

        # DCS Channel Assignments
        dcs_channels_df = create_channel_assignments_df(result.dcs_cards, 'DCS')
        if not dcs_channels_df.empty:
            dcs_channels_df.to_excel(writer, sheet_name='DCS Channels', index=False)

        # SIS Channel Assignments
        sis_channels_df = create_channel_assignments_df(result.sis_cards, 'SIS')
        if not sis_channels_df.empty:
            sis_channels_df.to_excel(writer, sheet_name='SIS Channels', index=False)

        # RTU Channel Assignments
        rtu_channels_df = create_channel_assignments_df(result.rtu_cards, 'RTU')
        if not rtu_channels_df.empty:
            rtu_channels_df.to_excel(writer, sheet_name='RTU Channels', index=False)

    output.seek(0)
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='io_allocation.xlsx'
    )


@app.route('/api/io-allocation/generate-pdf', methods=['POST'])
def generate_io_allocation_pdf():
    """Generate PDF report for I/O allocation."""
    from src.drawing.io_allocation_report import generate_io_allocation_report, ReportConfig

    data = request.json
    session_id = data.get('session_id')

    if session_id not in io_allocation_store:
        return jsonify({'error': 'Session not found'}), 404

    stored = io_allocation_store[session_id]
    result = stored['result']
    vendor = stored.get('vendor', 'Yokogawa')

    output_path = OUTPUT_FOLDER / f'io_allocation_{session_id}.pdf'
    config = ReportConfig(
        project_name="I/O Card Allocation Report",
        project_number="",
        vendor=vendor
    )

    generate_io_allocation_report(result, str(output_path), config)

    return send_file(
        output_path,
        mimetype='application/pdf',
        as_attachment=True,
        download_name='io_allocation_report.pdf'
    )


# ============================================================================
# I/O ALLOCATION CHAT ROUTES (AI-Assisted with RAG)
# ============================================================================

# Store for chat sessions (in-memory)
chat_sessions = {}

# Claude API key for RAG assistant (loaded from environment)
CLAUDE_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')


@app.route('/io-allocation/chat')
def io_allocation_chat_page():
    """AI-assisted I/O allocation chat interface."""
    return render_template('io_allocation_chat.html')


@app.route('/api/io-allocation/chat/start', methods=['POST'])
def start_chat_session():
    """Start a new chat session with I/O list upload."""
    import uuid

    try:
        # Check for I/O list file
        if 'io_list' not in request.files:
            return jsonify({'error': 'No I/O list file provided'}), 400

        io_list_file = request.files['io_list']
        vendor = request.form.get('vendor', 'Yokogawa')

        if io_list_file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        # Save I/O list file
        filename = secure_filename(io_list_file.filename)
        filepath = UPLOAD_FOLDER / filename
        io_list_file.save(filepath)

        # Parse I/O list to get instrument count
        file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''

        if file_ext == 'pdf':
            try:
                from src.parsers.pdf_extractor import PDFExtractor
                extractor = PDFExtractor()
                extraction_result = extractor.extract_from_file(str(filepath))
                instruments = extractor.to_instruments(extraction_result.instruments)
            except Exception as e:
                return jsonify({'error': f'PDF extraction error: {str(e)}'}), 400
        else:
            result = load_io_list(str(filepath))
            if not result.is_valid:
                errors = [e.message for e in result.validation_result.errors]
                return jsonify({'error': f'Validation errors: {", ".join(errors)}'}), 400
            instruments = result.instruments

        if not instruments:
            return jsonify({'error': 'No instruments found in file'}), 400

        # Initialize RAG assistant
        from src.services.rag_service import RAGAssistant
        assistant = RAGAssistant(api_key=CLAUDE_API_KEY)

        # Add I/O list summary to assistant's knowledge base
        from collections import Counter
        from src.parsers.flexible_parser import infer_io_type_from_instrument_type

        # Build I/O type counts - infer if not set
        io_counts = Counter()
        inst_type_counts = Counter()
        for inst in instruments:
            # Get or infer I/O type
            if hasattr(inst, 'io_type') and inst.io_type:
                io_type = inst.io_type
            else:
                io_type = infer_io_type_from_instrument_type(inst.instrument_type) or 'UNKNOWN'
            io_counts[io_type] += 1
            inst_type_counts[inst.instrument_type] += 1

        area_counts = Counter(inst.area for inst in instruments)

        # Create detailed I/O list summary with best practices assumptions
        io_list_summary = f"""I/O LIST SUMMARY - {filename}
Total Instruments: {len(instruments)}

I/O TYPE BREAKDOWN:
"""
        total_with_types = 0
        for io_type in ['AI', 'AO', 'DI', 'DO']:
            count = io_counts.get(io_type, 0)
            if count > 0:
                io_list_summary += f"- {io_type}: {count} instruments\n"
                total_with_types += count

        if io_counts.get('UNKNOWN', 0) > 0:
            io_list_summary += f"- UNKNOWN/OTHER: {io_counts['UNKNOWN']} instruments\n"

        io_list_summary += f"\nAREA DISTRIBUTION:\n"
        for area, count in sorted(area_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            io_list_summary += f"- Area {area}: {count} instruments\n"

        io_list_summary += f"\nTOP INSTRUMENT TYPES:\n"
        for inst_type, count in inst_type_counts.most_common(10):
            io_list_summary += f"- {inst_type}: {count} instruments\n"

        io_list_summary += f"\nSAMPLE INSTRUMENTS (first 20):\n"
        for i, inst in enumerate(instruments[:20], 1):
            io_type = getattr(inst, 'io_type', None) or infer_io_type_from_instrument_type(inst.instrument_type) or 'N/A'
            io_list_summary += f"{i}. {inst.tag_number} - {inst.instrument_type} ({io_type}) - Area {inst.area}\n"

        if len(instruments) > 20:
            io_list_summary += f"\n... and {len(instruments) - 20} more instruments"

        # Add best practices assumptions
        io_list_summary += f"""

DESIGN ASSUMPTIONS (Based on Industry Best Practices):
- Spare Capacity: 20% (standard for DCS/RTU unless specified otherwise)
- Segregation: No IS/non-IS segregation mentioned - assuming standard non-IS system
- SIL Rating: Not specified - assuming non-safety (DCS) system
- Cabinet Distribution: Will optimize by area to minimize cable runs
- Voltage Levels: Standard 24VDC for discrete signals, 4-20mA for analog

NOTE: If any of these assumptions are incorrect, please provide the specific requirements.
"""

        # Add to assistant's document store
        assistant.add_reference_document(f"IO_LIST_{filename}", io_list_summary)

        # Handle spec file uploads
        spec_files = request.files.getlist('specs')
        for spec_file in spec_files:
            if spec_file and spec_file.filename:
                spec_filename = secure_filename(spec_file.filename)
                spec_path = UPLOAD_FOLDER / f"spec_{spec_filename}"
                spec_file.save(spec_path)

                # Extract text from spec PDF
                from src.services.rag_service import extract_text_from_pdf
                spec_text = extract_text_from_pdf(str(spec_path))
                if spec_text:
                    assistant.add_reference_document(spec_filename, spec_text)

        # Generate session ID
        session_id = str(uuid.uuid4())[:8]

        # Get system type from parse result if available
        system_type = getattr(result, 'system_type', None) if file_ext != 'pdf' else None

        # Store session
        chat_sessions[session_id] = {
            'assistant': assistant,
            'instruments': instruments,
            'filename': filename,
            'vendor': vendor,
            'filepath': str(filepath),
            'system_type': system_type
        }

        # Get initial greeting
        greeting = assistant.get_initial_greeting(filename, len(instruments))

        return jsonify({
            'session_id': session_id,
            'greeting': greeting,
            'instrument_count': len(instruments),
            'filename': filename
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/io-allocation/chat/message', methods=['POST'])
def chat_message():
    """Handle chat message in a session."""
    try:
        data = request.json
        session_id = data.get('session_id')
        message = data.get('message', '').strip()

        if not session_id or session_id not in chat_sessions:
            return jsonify({'error': 'Session not found'}), 404

        if not message:
            return jsonify({'error': 'No message provided'}), 400

        session = chat_sessions[session_id]
        assistant = session['assistant']

        # Get response from assistant
        response = assistant.chat(message)

        # Check if user is ready to proceed
        ready_to_proceed = False

        # Broader set of trigger phrases - show button when user wants to move forward
        proceed_phrases = [
            'proceed', 'confirm', 'yes', 'correct', 'go ahead', 'looks good',
            'that\'s right', 'generate', 'allocate', 'create', 'draw', 'calculate',
            'ok', 'okay', 'sure', 'agreed', 'accepted', 'approved', 'do it'
        ]

        # Show button if user confirms OR asks to generate
        if any(phrase in message.lower() for phrase in proceed_phrases):
            # Try to extract rules (optional, may not always have structured rules)
            rules = assistant.extract_confirmed_rules()

            # Consider ready if rules are confirmed OR if user explicitly asked to proceed
            if rules and rules.get('confirmed', False):
                ready_to_proceed = True
                session['confirmed_rules'] = rules
            elif any(action in message.lower() for action in ['generate', 'allocate', 'proceed', 'calculate', 'draw']):
                # User explicitly wants to proceed - show button even without formal rule extraction
                ready_to_proceed = True
                # Store minimal rules as default
                session['confirmed_rules'] = {
                    'confirmed': True,
                    'spare_percent': 0.20,
                    'segregate_by_area': True,
                    'segregate_is_non_is': False,
                    'max_cabinets_per_area': None,
                    'group_by_loop': False,
                    'custom_rules': [],
                    'summary': 'Standard 20% spare, area-based distribution, no special segregation'
                }

        return jsonify({
            'response': response,
            'ready_to_proceed': ready_to_proceed
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/io-allocation/chat/upload-spec', methods=['POST'])
def upload_spec_document():
    """Upload a reference specification document to an active session."""
    try:
        session_id = request.form.get('session_id')
        if not session_id or session_id not in chat_sessions:
            return jsonify({'error': 'Session not found'}), 404

        if 'spec' not in request.files:
            return jsonify({'error': 'No spec file provided'}), 400

        spec_file = request.files['spec']
        if not spec_file or not spec_file.filename:
            return jsonify({'error': 'No file selected'}), 400

        session = chat_sessions[session_id]
        assistant = session['assistant']

        # Save and process spec file
        spec_filename = secure_filename(spec_file.filename)
        spec_path = UPLOAD_FOLDER / f"spec_{session_id}_{spec_filename}"
        spec_file.save(spec_path)

        # Extract text
        from src.services.rag_service import extract_text_from_pdf
        spec_text = extract_text_from_pdf(str(spec_path))

        if spec_text:
            assistant.add_reference_document(spec_filename, spec_text)
            return jsonify({
                'success': True,
                'message': f'📄 Added reference document: **{spec_filename}**. I\'ll ensure compliance with this spec.'
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Could not extract text from {spec_filename}. Please ensure it\'s a readable PDF.'
            })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/io-allocation/chat/calculate', methods=['POST'])
def calculate_from_chat():
    """Execute I/O allocation based on chat session rules."""
    from src.engine.io_allocator import IOAllocator
    from src.services.llm_rules_service import AllocationRules
    from collections import defaultdict
    import math
    import uuid

    try:
        data = request.json
        chat_session_id = data.get('session_id')

        if not chat_session_id or chat_session_id not in chat_sessions:
            return jsonify({'error': 'Session not found'}), 404

        session = chat_sessions[chat_session_id]
        instruments = session['instruments']
        vendor = session['vendor']
        assistant = session['assistant']
        system_type_override = session.get('system_type')

        # Extract rules from conversation
        rules_data = assistant.extract_confirmed_rules()

        # Build AllocationRules from extracted data
        spare_percent = 0.20  # Default
        rules_applied = None

        if rules_data:
            spare_percent = rules_data.get('spare_percent', 0.20)

            # Create AllocationRules object
            rules_applied = AllocationRules(
                spare_percent=spare_percent,
                segregate_by_area=rules_data.get('segregate_by_area', False),
                segregate_is_non_is=rules_data.get('segregate_is_non_is', True),
                max_cabinets_per_area=rules_data.get('max_cabinets_per_area'),
                group_by_loop=rules_data.get('group_by_loop', False),
                custom_rules=rules_data.get('custom_rules', [])
            )
            rules_applied._interpretation = rules_data.get('summary', '')

        # Perform allocation
        allocator = IOAllocator(vendor=vendor, spare_percent=spare_percent)
        if rules_applied:
            allocator.custom_rules = rules_applied

        allocation_result = allocator.allocate(instruments, system_type_override=system_type_override)

        # Store in io_allocation_store for result page
        result_session_id = str(uuid.uuid4())[:8]

        io_allocation_store[result_session_id] = {
            'result': allocation_result,
            'instruments': instruments,
            'filename': session['filename'],
            'vendor': vendor,
            'rules_applied': rules_applied.to_dict() if rules_applied else None,
            'rules_interpretation': rules_data.get('summary', '') if rules_data else None
        }

        # Prepare template data (same as calculate_io_allocation_route)
        def prepare_allocation_rows(summary, cards):
            rows = []
            cards_by_type = defaultdict(list)
            for card in cards:
                cards_by_type[card.module.io_type.value].append(card)

            for io_type in ['AI', 'AO', 'DI', 'DO']:
                signal_count = summary.get(io_type, 0)
                type_cards = cards_by_type.get(io_type, [])

                if signal_count > 0 or type_cards:
                    module_model = type_cards[0].module.model if type_cards else 'N/A'
                    channels_per_card = type_cards[0].total_channels if type_cards else 0
                    total_channels = sum(c.total_channels for c in type_cards)
                    spare = total_channels - signal_count if total_channels > 0 else 0
                    spare_pct = round((spare / total_channels) * 100, 1) if total_channels > 0 else 0

                    rows.append({
                        'io_type': io_type,
                        'signal_count': signal_count,
                        'channels_needed': math.ceil(signal_count * 1.2) if signal_count > 0 else 0,
                        'module_model': module_model,
                        'channels_per_card': channels_per_card,
                        'cards_required': len(type_cards),
                        'spare_percent': spare_pct
                    })
            return rows

        dcs_allocation = prepare_allocation_rows(allocation_result.dcs_summary, allocation_result.dcs_cards)
        sis_allocation = prepare_allocation_rows(allocation_result.sis_summary, allocation_result.sis_cards)
        rtu_allocation = prepare_allocation_rows(allocation_result.rtu_summary, allocation_result.rtu_cards)

        # Prepare channel details
        def prepare_channel_details(cards):
            details = []
            for card in cards:
                channels = []
                for ch_num in sorted(card.channel_assignments.keys()):
                    ch_data = card.channel_assignments[ch_num]
                    channels.append({
                        'number': ch_num,
                        'tag': ch_data.get('tag', 'SPARE'),
                        'service': ch_data.get('service', ''),
                        'type': ch_data.get('type', ''),
                        'status': ch_data.get('status', 'SPARE')
                    })
                spare_pct = round((card.spare_channels / card.total_channels) * 100, 1) if card.total_channels > 0 else 0
                details.append({
                    'module': card.module.model,
                    'io_type': card.module.io_type.value,
                    'card_number': card.card_number,
                    'channels': channels,
                    'total': card.total_channels,
                    'used': card.used_channels,
                    'spare': card.spare_channels,
                    'spare_pct': spare_pct
                })
            return details

        channel_details = {
            'DCS': prepare_channel_details(allocation_result.dcs_cards),
            'SIS': prepare_channel_details(allocation_result.sis_cards),
            'RTU': prepare_channel_details(allocation_result.rtu_cards)
        }

        # Build custom rules display info
        custom_rules_info = None
        if rules_applied:
            custom_rules_info = {
                'interpretation': getattr(rules_applied, '_interpretation', ''),
                'spare_percent': rules_applied.spare_percent * 100,
                'rules': rules_applied.custom_rules,
                'segregate_by_area': rules_applied.segregate_by_area,
                'max_cabinets_per_area': rules_applied.max_cabinets_per_area,
                'group_by_loop': rules_applied.group_by_loop
            }

        # Clean up chat session
        del chat_sessions[chat_session_id]

        # Return redirect URL with rendered template info
        return jsonify({
            'redirect': f'/io-allocation/result/{result_session_id}'
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/io-allocation/result/<session_id>')
def io_allocation_result_page(session_id):
    """Display I/O allocation results for a session."""
    from collections import defaultdict
    import math

    if session_id not in io_allocation_store:
        flash('Session expired or not found. Please recalculate.', 'error')
        return redirect(url_for('io_allocation_page'))

    stored = io_allocation_store[session_id]
    allocation_result = stored['result']
    vendor = stored['vendor']
    rules_applied = stored.get('rules_applied')
    rules_interpretation = stored.get('rules_interpretation')

    # Prepare template data
    def prepare_allocation_rows(summary, cards):
        rows = []
        cards_by_type = defaultdict(list)
        for card in cards:
            cards_by_type[card.module.io_type.value].append(card)

        for io_type in ['AI', 'AO', 'DI', 'DO']:
            signal_count = summary.get(io_type, 0)
            type_cards = cards_by_type.get(io_type, [])

            if signal_count > 0 or type_cards:
                module_model = type_cards[0].module.model if type_cards else 'N/A'
                channels_per_card = type_cards[0].total_channels if type_cards else 0
                total_channels = sum(c.total_channels for c in type_cards)
                spare = total_channels - signal_count if total_channels > 0 else 0
                spare_pct = round((spare / total_channels) * 100, 1) if total_channels > 0 else 0

                rows.append({
                    'io_type': io_type,
                    'signal_count': signal_count,
                    'channels_needed': math.ceil(signal_count * 1.2) if signal_count > 0 else 0,
                    'module_model': module_model,
                    'channels_per_card': channels_per_card,
                    'cards_required': len(type_cards),
                    'spare_percent': spare_pct
                })
        return rows

    dcs_allocation = prepare_allocation_rows(allocation_result.dcs_summary, allocation_result.dcs_cards)
    sis_allocation = prepare_allocation_rows(allocation_result.sis_summary, allocation_result.sis_cards)
    rtu_allocation = prepare_allocation_rows(allocation_result.rtu_summary, allocation_result.rtu_cards)

    # Prepare channel details
    def prepare_channel_details(cards):
        details = []
        for card in cards:
            channels = []
            for ch_num in sorted(card.channel_assignments.keys()):
                ch_data = card.channel_assignments[ch_num]
                channels.append({
                    'number': ch_num,
                    'tag': ch_data.get('tag', 'SPARE'),
                    'service': ch_data.get('service', ''),
                    'type': ch_data.get('type', ''),
                    'status': ch_data.get('status', 'SPARE')
                })
            spare_pct = round((card.spare_channels / card.total_channels) * 100, 1) if card.total_channels > 0 else 0
            details.append({
                'module': card.module.model,
                'io_type': card.module.io_type.value,
                'card_number': card.card_number,
                'channels': channels,
                'total': card.total_channels,
                'used': card.used_channels,
                'spare': card.spare_channels,
                'spare_pct': spare_pct
            })
        return details

    channel_details = {
        'DCS': prepare_channel_details(allocation_result.dcs_cards),
        'SIS': prepare_channel_details(allocation_result.sis_cards),
        'RTU': prepare_channel_details(allocation_result.rtu_cards)
    }

    # Build custom rules info
    custom_rules_info = None
    if rules_applied:
        custom_rules_info = {
            'interpretation': rules_interpretation or '',
            'spare_percent': rules_applied.get('spare_percent', 0.20) * 100,
            'rules': rules_applied.get('custom_rules', []),
            'segregate_by_area': rules_applied.get('segregate_by_area', False),
            'max_cabinets_per_area': rules_applied.get('max_cabinets_per_area'),
            'group_by_loop': rules_applied.get('group_by_loop', False)
        }

    return render_template(
        'io_allocation.html',
        session_id=session_id,
        vendor=vendor,
        total_instruments=len(stored['instruments']),
        total_cards=allocation_result.total_cards,
        segregation_count=len(allocation_result.segregation_rules_applied),
        dcs_allocation=dcs_allocation,
        sis_allocation=sis_allocation,
        rtu_allocation=rtu_allocation,
        channel_details=channel_details,
        custom_rules_info=custom_rules_info,
        segregation_rules=allocation_result.segregation_rules_applied
    )


if __name__ == '__main__':
    print("=" * 60)
    print("DCS Interconnection Diagram Generator")
    print("=" * 60)
    print("\nStarting web server...")
    print("Open your browser and go to: http://localhost:5000")
    print("\nPress Ctrl+C to stop the server")
    print("=" * 60)
    app.run(debug=False, host='0.0.0.0', port=5000)
