"""
Flask web server for SEVEN area measurement tool.
Provides drag-drop DXF upload, processing, and Excel export via browser.
"""
import os
import tempfile
import traceback
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file

from src.config_loader import load_config
from src.dxf_parser import parse_dxf
from src.measurement_engine import compute_survey_area
from src.excel_writer import write_area_template
from src.validators import validate_dwg_file

# Get the absolute path to the template folder
template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
app = Flask(__name__, template_folder=template_dir)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file

# Load config once at startup
try:
    config = load_config()
except Exception as e:
    print(f"ERROR: Failed to load config: {e}")
    config = None


@app.route('/')
def index():
    """Serve the main upload page."""
    return render_template('index.html')


@app.route('/api/upload', methods=['POST'])
def upload_file():
    """
    Accept DXF file, process it, and return Excel results.
    
    Request: multipart form-data with 'file' field (DXF file)
    Response: JSON with success status, messages, and download URL OR error details
    """
    if config is None:
        return jsonify({'success': False, 'error': 'Configuration not loaded. Check server logs.'}), 500
    
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400
    
    if not file.filename.lower().endswith('.dxf'):
        return jsonify({'success': False, 'error': 'File must be a .dxf file'}), 400
    
    # Save uploaded file to temp location
    with tempfile.NamedTemporaryFile(suffix='.dxf', delete=False) as tmp_dxf:
        try:
            file.save(tmp_dxf.name)
            tmp_dxf_path = tmp_dxf.name
        except Exception as e:
            return jsonify({'success': False, 'error': f'Failed to save file: {e}'}), 500
    
    # Create temp output file for Excel
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_xlsx:
        tmp_xlsx_path = tmp_xlsx.name
    
    try:
        # Step 1: Validate DWG (warnings only, don't fail)
        is_valid, messages = validate_dwg_file(tmp_dxf_path)
        warnings = [m for m in messages if m.startswith('WARNING:')]
        
        # Step 2: Parse DXF
        regions = parse_dxf(tmp_dxf_path)
        if not regions:
            os.unlink(tmp_dxf_path)
            os.unlink(tmp_xlsx_path)
            return jsonify({
                'success': False,
                'error': 'No regions found in DXF. Ensure drawing contains labeled, enclosed polygons.'
            }), 400
        
        # Step 3: Compute survey areas
        surveys = {}
        measurement_results = []
        for survey_id in ['GLA', 'GFA', 'BUA', 'Project_Area']:
            try:
                result = compute_survey_area(regions, survey_id)
                surveys[survey_id] = result.area_sqm
                measurement_results.append(result)
            except Exception as e:
                surveys[survey_id] = 0.0
        
        # Step 4: Export to Excel
        write_area_template(tmp_xlsx_path, measurement_results)
        
        # Return success with download URL
        return jsonify({
            'success': True,
            'message': f'Processed {len(regions)} region(s) successfully.',
            'regions_found': len(regions),
            'surveys': surveys,
            'warnings': warnings,
            'download_url': '/api/download?file=' + os.path.basename(tmp_xlsx_path)
        }), 200
    
    except Exception as e:
        # Log full traceback
        print(f"ERROR processing DXF: {e}")
        traceback.print_exc()
        
        # Cleanup temp files
        try:
            os.unlink(tmp_dxf_path)
            os.unlink(tmp_xlsx_path)
        except:
            pass
        
        return jsonify({
            'success': False,
            'error': f'Processing failed: {str(e)}'
        }), 500
    
    finally:
        # Cleanup input DXF temp file (keep .xlsx for download)
        try:
            os.unlink(tmp_dxf_path)
        except:
            pass


@app.route('/api/download', methods=['GET'])
def download_file():
    """Download the generated Excel file."""
    filename = request.args.get('file')
    if not filename:
        return jsonify({'error': 'No file specified'}), 400
    
    filepath = os.path.join(tempfile.gettempdir(), filename)
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404
    
    try:
        return send_file(filepath, as_attachment=True, download_name='area_measurements.xlsx')
    finally:
        # Clean up after download
        try:
            os.unlink(filepath)
        except:
            pass


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'ok',
        'config_loaded': config is not None
    }), 200


if __name__ == '__main__':
    print("Starting SEVEN Area Calculator web server...")
    print("Open http://localhost:5000 in your browser")
    app.run(debug=False, host='127.0.0.1', port=5000)
