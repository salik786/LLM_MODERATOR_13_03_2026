"""
Admin API Endpoints - COMPLETE FIXED VERSION WITH OPENAI SUPPORT
===================
Backend API for admin panel - Fixed room creation with max_participants
"""

import logging
import csv
import json
from io import StringIO
from datetime import datetime, timezone
from flask import Blueprint, jsonify, request, make_response
from supabase_client import (
    supabase,
    get_room,
    get_participants,
    get_chat_history,
    get_participants_with_details,
    create_room,
    create_room_admin,  # IMPORT THE ADMIN VERSION WITH max_participants
    update_room_status,
    end_session,
    add_message,
    get_messages_for_export,
    get_all_rooms as get_all_rooms_from_db,
    get_system_stats as get_system_stats_from_db,
    get_room_stats as get_room_stats_from_db,
    log_admin_action,
    create_export_record,
)

logger = logging.getLogger("ADMIN_API")

# Create blueprint
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# ============================================================
# Helper: Safe datetime parsing
# ============================================================

def safe_datetime_parse(dt_str):
    """Safely parse datetime string to avoid timezone issues"""
    if not dt_str:
        return None
    try:
        dt_str = dt_str.replace('Z', '+00:00')
        if '+' in dt_str:
            return datetime.fromisoformat(dt_str)
        else:
            return datetime.fromisoformat(dt_str + '+00:00')
    except:
        try:
            return datetime.strptime(dt_str.split('.')[0], '%Y-%m-%dT%H:%M:%S')
        except:
            return datetime.now(timezone.utc)

# ============================================================
# ✅ FIXED: Admin Room Creation - NOW WORKING WITH max_participants
# ============================================================

@admin_bp.route('/rooms', methods=['POST'])
def create_room_admin_endpoint():
    """Admin-only room creation endpoint - FIXED to use create_room_admin"""
    try:
        data = request.json or {}
        
        mode = data.get('mode', 'active')
        story_id = data.get('story_id')
        max_participants = int(data.get('max_participants', 3))
        admin_note = data.get('admin_note', '')
        admin_user = data.get('admin_user', 'admin')
        
        # Validate
        if mode not in ['active', 'passive']:
            return jsonify({"error": "Mode must be 'active' or 'passive'"}), 400
        
        if max_participants < 1 or max_participants > 10:
            return jsonify({"error": "Max participants must be between 1 and 10"}), 400
        
        # Import here to avoid circular imports
        from data_retriever import get_data
        
        # Get story
        if story_id:
            story_data = get_data(story_id)
            if not story_data:
                return jsonify({"error": f"Story {story_id} not found"}), 404
        else:
            story_data = get_data()
            story_id = story_data.get('story_id', 'default-story')
        
        # ✅ FIXED: Use create_room_admin which accepts max_participants
        room = create_room_admin(
            mode=mode,
            story_id=story_id,
            max_participants=max_participants,
            created_by=f'admin:{admin_user}',
            admin_note=admin_note
        )
        
        # Log the creation
        log_admin_action('create_room', 'room', room['id'], {
            'mode': mode,
            'story_id': story_id,
            'max_participants': max_participants,
            'admin_note': admin_note
        }, admin_user)
        
        logger.info(f"✅ Admin created room: {room['id']} (mode={mode}, max_participants={max_participants})")
        
        return jsonify({
            "success": True,
            "room": room,
            "shareable_link": f"/join/{mode}",
            "admin_link": f"/admin/rooms/{room['id']}"
        })
    
    except Exception as e:
        logger.error(f"❌ Error creating room as admin: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

# ============================================================
# FIXED: Enhanced Room Details with Usernames
# ============================================================

@admin_bp.route('/rooms/<room_id>', methods=['GET'])
def get_room_details(room_id: str):
    """Get detailed room information including participants and messages"""
    try:
        room = get_room(room_id)
        if not room:
            return jsonify({"error": "Room not found"}), 404
        
        # Get participants with proper usernames
        participants = get_participants_with_details(room_id)
        
        # Get messages
        messages = get_messages_for_export(room_id)
        
        # Get session info
        session_response = supabase.table('sessions').select('*').eq('room_id', room_id).execute()
        sessions = session_response.data if session_response.data else []
        
        # Get stats
        stats = get_room_stats_from_db(room_id)
        
        logger.info(f"📊 Admin: Viewed room {room_id} with {len(participants)} participants, {len(messages)} messages")
        
        return jsonify({
            "room": room,
            "participants": participants,
            "messages": messages,
            "sessions": sessions,
            "stats": stats
        })
    
    except Exception as e:
        logger.error(f"❌ Error getting room details: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

# ============================================================
# FIXED: Chat Export Endpoints
# ============================================================

@admin_bp.route('/rooms/<room_id>/export/chat', methods=['GET'])
def export_room_chat(room_id: str):
    """Export chat messages in various formats"""
    try:
        format_type = request.args.get('format', 'json').lower()
        
        # Get messages
        messages = get_messages_for_export(room_id)
        
        if not messages:
            return jsonify({"error": "No messages found for this room"}), 404
        
        # Get room info for filename
        room = get_room(room_id)
        
        # Export based on format
        if format_type == 'json':
            return jsonify({
                "room_id": room_id,
                "room_mode": room.get('mode') if room else 'unknown',
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "message_count": len(messages),
                "messages": messages
            })
        
        elif format_type == 'csv':
            output = StringIO()
            if messages:
                fieldnames = ['id', 'username', 'message', 'message_type', 'created_at', 'word_count']
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(messages)
            
            csv_data = output.getvalue()
            output.close()
            
            response = make_response(csv_data)
            response.headers['Content-Type'] = 'text/csv'
            response.headers['Content-Disposition'] = f'attachment; filename=chat_{room_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
            
            create_export_record(room_id, 'chat', 'csv')
            
            return response
        
        elif format_type == 'tsv':
            output = StringIO()
            if messages:
                fieldnames = ['id', 'username', 'message', 'message_type', 'created_at', 'word_count']
                writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter='\t')
                writer.writeheader()
                writer.writerows(messages)
            
            tsv_data = output.getvalue()
            output.close()
            
            response = make_response(tsv_data)
            response.headers['Content-Type'] = 'text/tab-separated-values'
            response.headers['Content-Disposition'] = f'attachment; filename=chat_{room_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.tsv'
            
            create_export_record(room_id, 'chat', 'tsv')
            
            return response
        
        else:
            return jsonify({"error": f"Unsupported format: {format_type}. Use json, csv, or tsv"}), 400
    
    except Exception as e:
        logger.error(f"❌ Error exporting chat: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

# ============================================================
# FIXED: Enhanced Room List
# ============================================================

@admin_bp.route('/rooms', methods=['GET'])
def get_all_rooms():
    """Get all rooms with filters"""
    try:
        # Get query parameters
        status = request.args.get('status')
        mode = request.args.get('mode')
        limit = int(request.args.get('limit', 50))
        search = request.args.get('search', '')
        
        # Use the function from supabase_client
        rooms = get_all_rooms_from_db(status, mode, limit)
        
        # Apply search filter if provided
        if search:
            rooms = [r for r in rooms if 
                    search.lower() in r.get('id', '').lower() or
                    search.lower() in r.get('story_id', '').lower() or
                    any(search.lower() in p.get('username', '').lower() or 
                        search.lower() in p.get('display_name', '').lower() 
                        for p in r.get('participant_list', []))]
        
        logger.info(f"📊 Admin: Retrieved {len(rooms)} rooms (status={status}, mode={mode})")
        return jsonify({
            "rooms": rooms,
            "count": len(rooms),
            "filters": {"status": status, "mode": mode, "search": search},
            "summary": {
                "total": len(rooms),
                "waiting": len([r for r in rooms if r.get('status') == 'waiting']),
                "active": len([r for r in rooms if r.get('status') == 'active']),
                "completed": len([r for r in rooms if r.get('status') == 'completed']),
                "active_mode": len([r for r in rooms if r.get('mode') == 'active']),
                "passive_mode": len([r for r in rooms if r.get('mode') == 'passive'])
            }
        })
    
    except Exception as e:
        logger.error(f"❌ Error getting rooms: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

# ============================================================
# FIXED: Enhanced Statistics
# ============================================================

@admin_bp.route('/stats', methods=['GET'])
def get_stats():
    """Get overall statistics"""
    try:
        stats = get_system_stats_from_db()
        logger.info(f"📊 Admin: Retrieved enhanced statistics")
        return jsonify(stats)
    
    except Exception as e:
        logger.error(f"❌ Error getting stats: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

# ============================================================
# FIXED: Room Control Endpoints
# ============================================================

@admin_bp.route('/rooms/<room_id>/end', methods=['POST'])
def end_room_session(room_id: str):
    """End a room session (admin control)"""
    try:
        data = request.json or {}
        admin_user = data.get('admin_user', 'admin')
        
        room = get_room(room_id)
        if not room:
            return jsonify({"error": "Room not found"}), 404
        
        # Import socketio to trigger session end with summaries
        from app import socketio as app_socketio
        
        # Trigger the socket event to end session with summaries
        app_socketio.emit("end_session", {
            "room_id": room_id,
            "sender": f"admin:{admin_user}"
        }, room=room_id)
        
        logger.info(f"✅ Admin triggered session end for room {room_id}")
        
        return jsonify({
            "success": True,
            "message": "Session ending, summaries will be sent to participants",
            "room_id": room_id
        })
    
    except Exception as e:
        logger.error(f"❌ Error ending room: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

# ============================================================
# FIXED: Delete Room Endpoint
# ============================================================

@admin_bp.route('/rooms/<room_id>', methods=['DELETE'])
def delete_room(room_id: str):
    """Delete a room and all associated data"""
    try:
        # Check if room exists
        room = get_room(room_id)
        if not room:
            return jsonify({"error": "Room not found"}), 404
        
        # Delete associated data in order
        supabase.table('messages').delete().eq('room_id', room_id).execute()
        supabase.table('participants').delete().eq('room_id', room_id).execute()
        supabase.table('sessions').delete().eq('room_id', room_id).execute()
        
        try:
            supabase.table('room_exports').delete().eq('room_id', room_id).execute()
        except:
            pass
        
        supabase.table('rooms').delete().eq('id', room_id).execute()
        
        log_admin_action('delete_room', 'room', room_id, {'room_mode': room.get('mode')})
        
        logger.info(f"🗑️ Admin: Deleted room {room_id}")
        return jsonify({"success": True, "message": "Room deleted successfully"})
    
    except Exception as e:
        logger.error(f"❌ Error deleting room: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

# ============================================================
# FIXED: Update Room Status
# ============================================================

@admin_bp.route('/rooms/<room_id>/status', methods=['PUT'])
def update_room_status_admin(room_id: str):
    """Update room status (admin control)"""
    try:
        data = request.json or {}
        status = data.get('status')
        admin_user = data.get('admin_user', 'admin')
        
        if status not in ['waiting', 'active', 'completed']:
            return jsonify({"error": "Invalid status. Use: waiting, active, completed"}), 400
        
        room = get_room(room_id)
        if not room:
            return jsonify({"error": "Room not found"}), 404
        
        update_room_status(room_id, status)
        
        if room.get('status') != status:
            add_message(
                room_id=room_id,
                username="System",
                message=f"Room status changed to '{status}' by admin.",
                message_type="system",
                metadata={"admin_action": True, "admin_user": admin_user}
            )
        
        log_admin_action('update_room_status', 'room', room_id, {
            'old_status': room.get('status'),
            'new_status': status
        }, admin_user)
        
        logger.info(f"✅ Admin updated room {room_id} status to {status}")
        
        return jsonify({
            "success": True,
            "message": f"Room status updated to {status}",
            "room_id": room_id,
            "old_status": room.get('status'),
            "new_status": status
        })
    
    except Exception as e:
        logger.error(f"❌ Error updating room status: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

# ============================================================
# Settings Management - UPDATED WITH OPENAI SUPPORT
# ============================================================

@admin_bp.route('/settings', methods=['GET'])
def get_all_settings():
    """Get all configuration settings grouped by category"""
    try:
        response = supabase.table('settings').select('*').order('category').execute()
        
        settings = response.data if response.data else []
        
        # Group by category
        grouped = {}
        for setting in settings:
            category = setting.get('category', 'general')
            if category not in grouped:
                grouped[category] = []
            grouped[category].append(setting)
        
        logger.info(f"📊 Admin: Retrieved {len(settings)} settings")
        return jsonify({
            "settings": settings,
            "grouped": grouped,
            "count": len(settings)
        })
    
    except Exception as e:
        logger.error(f"❌ Error getting settings: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/settings/<key>', methods=['GET'])
def get_setting(key: str):
    """Get specific setting by key"""
    try:
        response = supabase.table('settings').select('*').eq('key', key).maybe_single().execute()
        
        if not response.data:
            return jsonify({"error": "Setting not found"}), 404
        
        return jsonify(response.data)
    
    except Exception as e:
        logger.error(f"❌ Error getting setting {key}: {e}")
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/settings/<key>', methods=['PUT'])
def update_setting(key: str):
    """Update a setting value"""
    try:
        data = request.json
        new_value = data.get('value')
        
        if new_value is None:
            return jsonify({"error": "Value is required"}), 400
        
        # Check if setting exists
        check = supabase.table('settings').select('*').eq('key', key).maybe_single().execute()
        
        if check.data:
            # Update existing
            response = supabase.table('settings').update({
                'value': str(new_value),
                'updated_by': data.get('updated_by', 'admin'),
                'updated_at': datetime.now(timezone.utc).isoformat()
            }).eq('key', key).execute()
        else:
            # Create new setting with default type
            response = supabase.table('settings').insert({
                'key': key,
                'value': str(new_value),
                'data_type': 'string',
                'category': 'llm',
                'description': f'Setting for {key}',
                'updated_by': data.get('updated_by', 'admin'),
                'updated_at': datetime.now(timezone.utc).isoformat(),
                'created_at': datetime.now(timezone.utc).isoformat()
            }).execute()
        
        log_admin_action('update_setting', 'setting', None, {
            'key': key,
            'new_value': new_value
        }, data.get('admin_user', 'unknown'))
        
        logger.info(f"✅ Admin: Updated setting {key} = {new_value}")
        return jsonify(response.data[0] if response.data else {"success": True})
    
    except Exception as e:
        logger.error(f"❌ Error updating setting {key}: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

# ============================================================
# Admin Logs
# ============================================================

@admin_bp.route('/logs', methods=['GET'])
def get_admin_logs():
    """Get admin activity logs"""
    try:
        limit = int(request.args.get('limit', 100))
        
        response = (
            supabase.table('admin_logs')
            .select('*')
            .order('created_at', desc=True)
            .limit(limit)
            .execute()
        )
        
        logs = response.data if response.data else []
        
        return jsonify({
            "logs": logs,
            "count": len(logs)
        })
    
    except Exception as e:
        logger.error(f"❌ Error getting admin logs: {e}")
        return jsonify({"error": str(e)}), 500

# ============================================================
# Helper: Get Setting Value - UPDATED WITH BETTER ERROR HANDLING
# ============================================================

def get_setting_value(key: str, default=None):
    """Get a setting value from database with type conversion."""
    try:
        # Use maybe_single() instead of single() to avoid 404 errors
        response = supabase.table('settings').select('*').eq('key', key).maybe_single().execute()
        
        if not response.data:
            logger.debug(f"Setting {key} not found, using default: {default}")
            return default
        
        setting = response.data
        value_str = setting.get('value')
        data_type = setting.get('data_type', 'string')
        
        if value_str is None:
            return default
        
        try:
            if data_type == 'integer':
                return int(value_str)
            elif data_type == 'float':
                return float(value_str)
            elif data_type == 'boolean':
                return value_str.lower() in ('true', '1', 'yes', 'on')
            else:
                return value_str
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to convert setting {key} value '{value_str}' to {data_type}: {e}")
            return default
    
    except Exception as e:
        logger.warning(f"Failed to get setting {key}, using default: {e}")
        return default

# ============================================================
# RESEARCH EXPORT ENDPOINTS - SINGLE VERSION (NO DUPLICATES)
# ============================================================

@admin_bp.route('/research/export', methods=['GET'])
def export_research_data():
    """Export all research data for analysis (JSON or CSV)"""
    try:
        format_type = request.args.get('format', 'json').lower()
        condition = request.args.get('condition')  # 'active' or 'passive'
        
        # Get all completed rooms with their data
        query = supabase.table("rooms")\
            .select("""
                id,
                mode,
                condition,
                created_at,
                ended_at,
                final_ranking,
                research_metrics(*),
                moderator_interventions(*),
                participant_metrics(*),
                task_results(*)
            """)\
            .not_.is_("ended_at", "null")\
            .order("created_at", desc=True)
        
        if condition:
            query = query.eq("mode", condition)
        
        response = query.execute()
        rooms = response.data if response.data else []
        
        # Calculate summary statistics
        summary = {
            "total_sessions": len(rooms),
            "active_sessions": len([r for r in rooms if r.get('mode') == 'active']),
            "passive_sessions": len([r for r in rooms if r.get('mode') == 'passive']),
            "avg_gini": 0,
            "avg_dominance_gap": 0,
            "avg_accuracy": 0,
            "total_conflicts": 0,
            "total_interventions": 0
        }
        
        # Calculate averages
        gini_values = []
        dominance_values = []
        accuracy_values = []
        conflict_counts = []
        intervention_counts = []
        
        for room in rooms:
            if room.get('research_metrics'):
                for metric in room['research_metrics']:
                    if metric.get('gini_coefficient'):
                        gini_values.append(metric['gini_coefficient'])
                    if metric.get('dominance_gap'):
                        dominance_values.append(metric['dominance_gap'])
                    if metric.get('ranking_accuracy'):
                        accuracy_values.append(metric['ranking_accuracy'])
                    if metric.get('conflict_count'):
                        conflict_counts.append(metric['conflict_count'])
            
            if room.get('moderator_interventions'):
                intervention_counts.append(len(room['moderator_interventions']))
        
        if gini_values:
            summary['avg_gini'] = sum(gini_values) / len(gini_values)
        if dominance_values:
            summary['avg_dominance_gap'] = sum(dominance_values) / len(dominance_values)
        if accuracy_values:
            summary['avg_accuracy'] = sum(accuracy_values) / len(accuracy_values)
        if conflict_counts:
            summary['avg_conflicts_per_session'] = sum(conflict_counts) / len(conflict_counts)
        if intervention_counts:
            summary['avg_interventions_per_session'] = sum(intervention_counts) / len(intervention_counts)
        
        # Return based on format
        if format_type == 'json':
            return jsonify({
                "success": True,
                "summary": summary,
                "rooms": rooms,
                "exported_at": datetime.now(timezone.utc).isoformat()
            })
        
        elif format_type == 'csv':
            # Create CSV with flattened data
            output = StringIO()
            writer = csv.writer(output)
            
            # Header
            writer.writerow([
                'room_id', 'condition', 'gini_coefficient', 'dominance_gap', 
                'ranking_accuracy', 'total_messages', 'conflict_count', 
                'intervention_count', 'time_to_consensus'
            ])
            
            for room in rooms:
                metrics = room.get('research_metrics', [{}])[0] if room.get('research_metrics') else {}
                writer.writerow([
                    room['id'],
                    room.get('mode'),
                    metrics.get('gini_coefficient', ''),
                    metrics.get('dominance_gap', ''),
                    metrics.get('ranking_accuracy', ''),
                    metrics.get('total_messages', ''),
                    metrics.get('conflict_count', 0),
                    len(room.get('moderator_interventions', [])),
                    metrics.get('time_to_consensus', '')
                ])
            
            csv_data = output.getvalue()
            output.close()
            
            response = make_response(csv_data)
            response.headers['Content-Type'] = 'text/csv'
            response.headers['Content-Disposition'] = f'attachment; filename=research_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
            return response
        
        else:
            return jsonify({"error": f"Unsupported format: {format_type}. Use json or csv"}), 400
    
    except Exception as e:
        logger.error(f"❌ Error exporting research data: {e}")
        return jsonify({"error": str(e)}), 500


@admin_bp.route('/research/metrics/<room_id>', methods=['GET'])
def get_room_research_metrics(room_id: str):
    """Get detailed research metrics for a specific room"""
    try:
        # Get room info
        room_response = supabase.table("rooms").select("*").eq("id", room_id).maybe_single().execute()
        room = room_response.data if room_response.data else {}
        
        # Get metrics
        metrics_response = supabase.table("research_metrics").select("*").eq("room_id", room_id).execute()
        metrics = metrics_response.data if metrics_response.data else []
        
        # Get interventions
        interventions_response = supabase.table("moderator_interventions").select("*").eq("room_id", room_id).order("timestamp").execute()
        interventions = interventions_response.data if interventions_response.data else []
        
        # Get participant metrics
        participant_response = supabase.table("participant_metrics").select("*").eq("room_id", room_id).execute()
        participants = participant_response.data if participant_response.data else []
        
        # Get task results
        task_response = supabase.table("task_results").select("*").eq("room_id", room_id).execute()
        task = task_response.data[0] if task_response.data else {}
        
        return jsonify({
            "room": room,
            "metrics": metrics,
            "interventions": interventions,
            "participants": participants,
            "task": task
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting room metrics: {e}")
        return jsonify({"error": str(e)}), 500


@admin_bp.route('/research/summary', methods=['GET'])
def get_research_summary():
    """Get summary statistics comparing active vs passive conditions"""
    try:
        # Get all completed rooms
        rooms_response = supabase.table("rooms")\
            .select("id, mode")\
            .not_.is_("ended_at", "null")\
            .execute()
        
        rooms = rooms_response.data if rooms_response.data else []
        
        # Get all metrics
        metrics_response = supabase.table("research_metrics").select("*").execute()
        all_metrics = metrics_response.data if metrics_response.data else []
        
        # Separate by condition
        active_metrics = []
        passive_metrics = []
        
        for metric in all_metrics:
            room_id = metric.get('room_id')
            room = next((r for r in rooms if r['id'] == room_id), {})
            condition = room.get('mode')
            
            if condition == 'active':
                active_metrics.append(metric)
            elif condition == 'passive':
                passive_metrics.append(metric)
        
        def avg_metrics(metrics_list, key):
            values = [m.get(key) for m in metrics_list if m.get(key) is not None]
            return sum(values) / len(values) if values else 0
        
        summary = {
            "total_sessions": len(rooms),
            "active_sessions": len(active_metrics),
            "passive_sessions": len(passive_metrics),
            "active": {
                "avg_gini": avg_metrics(active_metrics, 'gini_coefficient'),
                "avg_dominance_gap": avg_metrics(active_metrics, 'dominance_gap'),
                "avg_conflict_count": avg_metrics(active_metrics, 'conflict_count'),
                "avg_repair_rate": avg_metrics(active_metrics, 'repair_rate'),
                "avg_accuracy": avg_metrics(active_metrics, 'ranking_accuracy'),
                "avg_messages": avg_metrics(active_metrics, 'total_messages'),
                "avg_time_to_consensus": avg_metrics(active_metrics, 'time_to_consensus'),
                "total_interventions": sum(metric.get('intervention_count', 0) for metric in active_metrics)
            },
            "passive": {
                "avg_gini": avg_metrics(passive_metrics, 'gini_coefficient'),
                "avg_dominance_gap": avg_metrics(passive_metrics, 'dominance_gap'),
                "avg_conflict_count": avg_metrics(passive_metrics, 'conflict_count'),
                "avg_repair_rate": avg_metrics(passive_metrics, 'repair_rate'),
                "avg_accuracy": avg_metrics(passive_metrics, 'ranking_accuracy'),
                "avg_messages": avg_metrics(passive_metrics, 'total_messages'),
                "avg_time_to_consensus": avg_metrics(passive_metrics, 'time_to_consensus'),
                "total_interventions": sum(metric.get('intervention_count', 0) for metric in passive_metrics)
            }
        }
        
        return jsonify(summary)
        
    except Exception as e:
        logger.error(f"❌ Error getting research summary: {e}")
        return jsonify({"error": str(e)}), 500