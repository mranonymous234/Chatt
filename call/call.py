# /call/call.py
from flask import Blueprint, render_template

call_bp = Blueprint('call', __name__, template_folder='templates', static_folder='static')

@call_bp.route('/<username>')
def call_user(username):
    """
    Serve the call page for the given username.
    """
    return render_template('call.html', username=username)
