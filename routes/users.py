from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User, Company, Role
from datetime import datetime

users_bp = Blueprint('users', __name__)


@users_bp.route('', methods=['GET'])
@jwt_required()
def get_users():
    """Получение списка всех пользователей (только для админов)"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        # Проверяем права доступа через role_obj
        if not current_user or not current_user.role_obj or current_user.role_obj.name != 'Администратор':
            return jsonify({'error': 'Доступ запрещен'}), 403
        
        users = User.query.all()
        
        return jsonify({
            'users': [user.to_dict() for user in users]
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Ошибка получения пользователей: {str(e)}'}), 500


@users_bp.route('/company', methods=['GET'])
@jwt_required()
def get_company_users():
    """Получение списка пользователей компании текущего пользователя"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        if not current_user or not current_user.parent_company_id:
            return jsonify({'error': 'Пользователь не привязан к компании'}), 400
        
        users = User.query.filter_by(parent_company_id=current_user.parent_company_id).all()
        
        return jsonify({
            'users': [user.to_dict() for user in users]
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Ошибка получения пользователей: {str(e)}'}), 500


@users_bp.route('/<string:user_id>', methods=['GET'])
@jwt_required()
def get_user(user_id):
    """Получение информации о пользователе"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'Пользователь не найден'}), 404
        
        # Проверяем права доступа
        if current_user.role != 'admin' and user.parent_company_id != current_user.parent_company_id:
            return jsonify({'error': 'Доступ запрещен'}), 403
        
        return jsonify(user.to_dict()), 200
        
    except Exception as e:
        return jsonify({'error': f'Ошибка получения пользователя: {str(e)}'}), 500


@users_bp.route('', methods=['POST'])
@jwt_required()
def create_user():
    """Создание нового пользователя"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        # Проверяем права доступа (проверяем через access_rights)
        if not current_user or not current_user.access_rights or not current_user.access_rights[0].can_manage_users:
            return jsonify({'error': 'Доступ запрещен'}), 403
        
        data = request.get_json()
        
        # Валидация данных
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Необходимо указать email и пароль'}), 400
        
        # Проверка формата email
        email = data['email'].strip().lower()
        if '@' not in email:
            return jsonify({'error': 'Неверный формат email'}), 400
        
        # Проверка существования пользователя
        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email уже используется'}), 400
        
        # Пользователь всегда создается в компании текущего пользователя
        parent_company_id = current_user.parent_company_id
        if not parent_company_id:
            return jsonify({'error': 'Текущий пользователь не привязан к компании'}), 400
        
        # Поиск роли по ID
        role_id = data.get('role')
        if not role_id:
            return jsonify({'error': 'Необходимо указать роль'}), 400
        
        role = Role.query.get(role_id)
        if not role:
            return jsonify({'error': 'Роль не найдена'}), 400
        
        # Создание пользователя
        user = User(
            email=email,
            role_id=role.id,
            parent_company_id=parent_company_id
        )
        user.set_password(data['password'])
        
        db.session.add(user)
        db.session.flush()  # Получаем ID пользователя
        
        # Создание прав доступа из данных фронтенда или полные права по умолчанию
        from models import AccessRight
        access_rights_data = data.get('access_rights', {})
        
        # Исключаем системные поля из создания
        excluded_keys = ['id', 'user_id', 'created_at', 'updated_at']
        filtered_data = {k: v for k, v in access_rights_data.items() if k not in excluded_keys}
        
        user_rights = AccessRight(
            user_id=user.id,
            can_view_monitoring=filtered_data.get('can_view_monitoring', True),
            can_view_notifications=filtered_data.get('can_view_notifications', True),
            can_view_locations=filtered_data.get('can_view_locations', True),
            can_view_reports=filtered_data.get('can_view_reports', True),
            can_view_admin=filtered_data.get('can_view_admin', True),
            can_manage_users=filtered_data.get('can_manage_users', True),
            can_manage_companies=filtered_data.get('can_manage_companies', True),
            can_view_security=filtered_data.get('can_view_security', True),
            can_manage_notifications=filtered_data.get('can_manage_notifications', True),
            can_create_locations=filtered_data.get('can_create_locations', True),
            can_edit_locations=filtered_data.get('can_edit_locations', True),
            can_delete_locations=filtered_data.get('can_delete_locations', True),
            can_create_containers=filtered_data.get('can_create_containers', True),
            can_edit_containers=filtered_data.get('can_edit_containers', True),
            can_delete_containers=filtered_data.get('can_delete_containers', True)
        )
        db.session.add(user_rights)
        db.session.commit()
        
        return jsonify({
            'message': 'Пользователь создан успешно',
            'user': user.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Ошибка создания пользователя: {str(e)}'}), 500


@users_bp.route('/<string:user_id>', methods=['PUT'])
@jwt_required()
def update_user(user_id):
    """Обновление пользователя"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'Пользователь не найден'}), 404
        
        # Проверяем права доступа
        if not current_user or not current_user.access_rights or not current_user.access_rights[0].can_manage_users:
            return jsonify({'error': 'Доступ запрещен'}), 403
        
        # Проверяем, что пользователь из той же компании
        if user.parent_company_id != current_user.parent_company_id:
            return jsonify({'error': 'Доступ запрещен'}), 403
        
        data = request.get_json()
        
        # Обновление полей
        if 'email' in data:
            email = data['email'].strip().lower()
            if '@' not in email:
                return jsonify({'error': 'Неверный формат email'}), 400
            
            # Проверка уникальности email
            existing_user = User.query.filter_by(email=email).first()
            if existing_user and existing_user.id != user_id:
                return jsonify({'error': 'Email уже используется'}), 400
            
            user.email = email
        
        if 'role' in data:
            role_id = data['role']
            if not role_id:
                return jsonify({'error': 'Необходимо указать роль'}), 400
            
            # Поиск роли по ID
            role = Role.query.get(role_id)
            if not role:
                return jsonify({'error': 'Роль не найдена'}), 400
            
            user.role_id = role.id
        
        if 'password' in data and data['password']:
            user.set_password(data['password'])
        
        # Обновление прав доступа
        if 'access_rights' in data:
            access_rights_data = data['access_rights']
            user_access_rights = user.access_rights[0] if user.access_rights else None
            
            # Исключаем системные поля из обновления
            excluded_keys = ['id', 'user_id', 'created_at', 'updated_at']
            
            if user_access_rights:
                # Обновляем существующие права
                for key, value in access_rights_data.items():
                    if key not in excluded_keys and hasattr(user_access_rights, key):
                        setattr(user_access_rights, key, value)
            else:
                # Создаем новые права доступа
                from models import AccessRight
                filtered_data = {k: v for k, v in access_rights_data.items() if k not in excluded_keys}
                user_access_rights = AccessRight(
                    user_id=user.id,
                    **filtered_data
                )
                db.session.add(user_access_rights)
        
        user.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'message': 'Пользователь обновлен успешно',
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Ошибка обновления пользователя: {str(e)}'}), 500


@users_bp.route('/<string:user_id>', methods=['DELETE'])
@jwt_required()
def delete_user(user_id):
    """Удаление пользователя"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'Пользователь не найден'}), 404
        
        # Проверяем права доступа
        if current_user.role != 'admin' and user.parent_company_id != current_user.parent_company_id:
            return jsonify({'error': 'Доступ запрещен'}), 403
        
        # Нельзя удалить самого себя
        if user.id == current_user_id:
            return jsonify({'error': 'Нельзя удалить самого себя'}), 400
        
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({'message': 'Пользователь удален успешно'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Ошибка удаления пользователя: {str(e)}'}), 500
