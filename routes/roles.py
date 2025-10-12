from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Role, AccessRight, User, Company

roles_bp = Blueprint('roles', __name__)


@roles_bp.route('', methods=['GET'])
@jwt_required()
def get_roles():
    """Получение списка всех глобальных ролей"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        if not current_user:
            return jsonify({'error': 'Пользователь не найден'}), 400
        
        roles = Role.query.all()
        
        return jsonify({
            'roles': [role.to_dict() for role in roles]
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Ошибка получения ролей: {str(e)}'}), 500


@roles_bp.route('', methods=['POST'])
@jwt_required()
def create_role():
    """Создание новой роли"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        # Проверяем права доступа (только владельцы и админы)
        if current_user.role not in ['owner', 'admin']:
            return jsonify({'error': 'Доступ запрещен'}), 403
        
        if not current_user.parent_company_id:
            return jsonify({'error': 'Пользователь не привязан к компании'}), 400
        
        data = request.get_json()
        
        # Валидация данных
        if not data or not data.get('name'):
            return jsonify({'error': 'Поле name обязательно'}), 400
        
        # Проверка уникальности имени роли в компании
        existing_role = Role.query.filter_by(
            name=data['name'], 
            company_id=current_user.parent_company_id
        ).first()
        
        if existing_role:
            return jsonify({'error': 'Роль с таким именем уже существует'}), 400
        
        # Создание роли
        role = Role(
            name=data['name'],
            description=data.get('description', ''),
            company_id=current_user.parent_company_id
        )
        
        db.session.add(role)
        db.session.flush()  # Получаем ID роли
        
        # Создание прав доступа по умолчанию
        access_rights = AccessRight(
            role_id=role.id,
            **data.get('access_rights', {})
        )
        
        db.session.add(access_rights)
        db.session.commit()
        
        # Загружаем созданную роль с правами
        role_with_rights = Role.query.get(role.id)
        
        return jsonify({
            'message': 'Роль создана успешно',
            'role': role_with_rights.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Ошибка создания роли: {str(e)}'}), 500


@roles_bp.route('/<string:role_id>', methods=['GET'])
@jwt_required()
def get_role(role_id):
    """Получение информации о роли"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        role = Role.query.get(role_id)
        if not role:
            return jsonify({'error': 'Роль не найдена'}), 404
        
        # Проверяем права доступа
        if role.company_id != current_user.parent_company_id:
            return jsonify({'error': 'Доступ запрещен'}), 403
        
        return jsonify(role.to_dict()), 200
        
    except Exception as e:
        return jsonify({'error': f'Ошибка получения роли: {str(e)}'}), 500


@roles_bp.route('/<string:role_id>', methods=['PUT'])
@jwt_required()
def update_role(role_id):
    """Обновление роли и её прав доступа"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        # Проверяем права доступа (только владельцы и админы)
        if current_user.role not in ['owner', 'admin']:
            return jsonify({'error': 'Доступ запрещен'}), 403
        
        role = Role.query.get(role_id)
        if not role:
            return jsonify({'error': 'Роль не найдена'}), 404
        
        # Проверяем права доступа
        if role.company_id != current_user.parent_company_id:
            return jsonify({'error': 'Доступ запрещен'}), 403
        
        data = request.get_json()
        
        # Обновление роли
        if 'name' in data:
            # Проверка уникальности имени
            existing_role = Role.query.filter_by(
                name=data['name'], 
                company_id=current_user.parent_company_id
            ).filter(Role.id != role_id).first()
            
            if existing_role:
                return jsonify({'error': 'Роль с таким именем уже существует'}), 400
            
            role.name = data['name']
        
        if 'description' in data:
            role.description = data['description']
        
        # Обновление прав доступа
        if 'access_rights' in data:
            access_rights = AccessRight.query.filter_by(role_id=role_id).first()
            if access_rights:
                for key, value in data['access_rights'].items():
                    if hasattr(access_rights, key):
                        setattr(access_rights, key, value)
        
        db.session.commit()
        
        # Загружаем обновленную роль с правами
        updated_role = Role.query.get(role_id)
        
        return jsonify({
            'message': 'Роль обновлена успешно',
            'role': updated_role.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Ошибка обновления роли: {str(e)}'}), 500


@roles_bp.route('/<string:role_id>', methods=['DELETE'])
@jwt_required()
def delete_role(role_id):
    """Удаление роли"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        # Проверяем права доступа (только владельцы и админы)
        if current_user.role not in ['owner', 'admin']:
            return jsonify({'error': 'Доступ запрещен'}), 403
        
        role = Role.query.get(role_id)
        if not role:
            return jsonify({'error': 'Роль не найдена'}), 404
        
        # Проверяем права доступа
        if role.company_id != current_user.parent_company_id:
            return jsonify({'error': 'Доступ запрещен'}), 403
        
        # Проверяем, не используется ли роль
        users_with_role = User.query.filter_by(role_id=role_id).count()
        if users_with_role > 0:
            return jsonify({'error': 'Роль используется пользователями и не может быть удалена'}), 400
        
        db.session.delete(role)
        db.session.commit()
        
        return jsonify({'message': 'Роль удалена успешно'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Ошибка удаления роли: {str(e)}'}), 500


@roles_bp.route('/<string:role_id>/access-rights', methods=['GET'])
@jwt_required()
def get_role_access_rights(role_id):
    """Получение прав доступа роли"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        role = Role.query.get(role_id)
        if not role:
            return jsonify({'error': 'Роль не найдена'}), 404
        
        # Проверяем права доступа
        if role.company_id != current_user.parent_company_id:
            return jsonify({'error': 'Доступ запрещен'}), 403
        
        access_rights = AccessRight.query.filter_by(role_id=role_id).first()
        if not access_rights:
            return jsonify({'error': 'Права доступа не найдены'}), 404
        
        return jsonify(access_rights.to_dict()), 200
        
    except Exception as e:
        return jsonify({'error': f'Ошибка получения прав доступа: {str(e)}'}), 500
