"""
API эндпоинты для управления FCM токенами
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, FCMToken, User
from datetime import datetime

bp = Blueprint('fcm', __name__, url_prefix='/api/fcm')


@bp.route('/token', methods=['POST'])
@jwt_required()
def save_fcm_token():
    """
    Сохранить FCM токен пользователя
    
    Request body:
    {
        "token": "fcm_token_string",
        "device_info": "optional device info"
    }
    """
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data or 'token' not in data:
            return jsonify({'error': 'FCM token required'}), 400
        
        token_string = data['token']
        device_info = data.get('device_info', request.headers.get('User-Agent', 'Unknown'))
        
        # Проверяем, существует ли уже этот токен
        existing_token = FCMToken.query.filter_by(token=token_string).first()
        
        if existing_token:
            # Если токен существует, обновляем время и device_info
            existing_token.updated_at = datetime.utcnow()
            existing_token.device_info = device_info
            # Если токен принадлежит другому пользователю, переназначаем
            if existing_token.user_id != user_id:
                existing_token.user_id = user_id
            print(f'✅ FCM токен обновлен для пользователя {user_id}')
        else:
            # Создаём новый токен
            fcm_token = FCMToken(
                user_id=user_id,
                token=token_string,
                device_info=device_info
            )
            db.session.add(fcm_token)
            print(f'✅ Новый FCM токен сохранен для пользователя {user_id}')
        
        db.session.commit()
        
        return jsonify({
            'message': 'FCM token saved successfully',
            'token_id': existing_token.id if existing_token else None
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f'❌ Ошибка сохранения FCM токена: {e}')
        return jsonify({'error': str(e)}), 500


@bp.route('/token', methods=['DELETE'])
@jwt_required()
def delete_fcm_token():
    """
    Удалить FCM токен пользователя (при выходе из приложения)
    
    Request body:
    {
        "token": "fcm_token_string"
    }
    """
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data or 'token' not in data:
            return jsonify({'error': 'FCM token required'}), 400
        
        token_string = data['token']
        
        # Удаляем токен
        fcm_token = FCMToken.query.filter_by(
            user_id=user_id,
            token=token_string
        ).first()
        
        if fcm_token:
            db.session.delete(fcm_token)
            db.session.commit()
            print(f'✅ FCM токен удален для пользователя {user_id}')
            return jsonify({'message': 'FCM token deleted successfully'}), 200
        else:
            return jsonify({'message': 'FCM token not found'}), 404
        
    except Exception as e:
        db.session.rollback()
        print(f'❌ Ошибка удаления FCM токена: {e}')
        return jsonify({'error': str(e)}), 500


@bp.route('/tokens', methods=['GET'])
@jwt_required()
def get_user_tokens():
    """
    Получить все FCM токены текущего пользователя
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        tokens = [token.to_dict() for token in user.fcm_tokens]
        
        return jsonify({
            'tokens': tokens,
            'count': len(tokens)
        }), 200
        
    except Exception as e:
        print(f'❌ Ошибка получения FCM токенов: {e}')
        return jsonify({'error': str(e)}), 500

