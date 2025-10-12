from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, 
    create_refresh_token,
    jwt_required, 
    get_jwt_identity
)
from models import db, User, Company

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST', 'OPTIONS'])
def register():
    """Регистрация нового пользователя"""
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
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
        
        # Проверка компании (опционально)
        parent_company_id = data.get('parent_company_id')
        if parent_company_id:
            company = Company.query.get(parent_company_id)
            if not company:
                return jsonify({'error': 'Компания не найдена'}), 404
        
        # Поиск роли по умолчанию (владелец)
        from models import Role
        default_role = Role.query.filter_by(name='Владелец').first()
        if not default_role:
            return jsonify({'error': 'Роль по умолчанию не найдена'}), 400
        
        # Создание пользователя
        user = User(
            email=email,
            role_id=default_role.id,
            parent_company_id=parent_company_id
        )
        user.set_password(data['password'])
        
        db.session.add(user)
        db.session.flush()  # Получаем ID пользователя
        
        # Создание прав доступа по умолчанию (полные права)
        from models import AccessRight
        default_rights = AccessRight(
            user_id=user.id,
            can_view_monitoring=True,
            can_view_notifications=True,
            can_view_locations=True,
            can_view_reports=True,
            can_view_admin=True,
            can_manage_users=True,
            can_manage_companies=True,
            can_view_security=True,
            can_manage_notifications=True,
            can_create_locations=True,
            can_edit_locations=True,
            can_delete_locations=True,
            can_create_containers=True,
            can_edit_containers=True,
            can_delete_containers=True
        )
        db.session.add(default_rights)
        db.session.commit()
        
        # Создание токенов
        access_token = create_access_token(identity=user.id)
        refresh_token = create_refresh_token(identity=user.id)
        
        return jsonify({
            'message': 'Регистрация успешна',
            'user': user.to_dict(),
            'access_token': access_token,
            'refresh_token': refresh_token
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Ошибка регистрации: {str(e)}'}), 500


@auth_bp.route('/login', methods=['POST', 'OPTIONS'])
def login():
    """Вход в систему"""
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        data = request.get_json()
        
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Необходимо указать email и пароль'}), 400
        
        # Поиск пользователя по email
        email = data['email'].strip().lower()
        user = User.query.filter_by(email=email).first()
        
        if not user or not user.check_password(data['password']):
            return jsonify({'error': 'Неверный email или пароль'}), 401
        
        # Создание токенов
        access_token = create_access_token(identity=user.id)
        refresh_token = create_refresh_token(identity=user.id)
        
        return jsonify({
            'message': 'Вход выполнен успешно',
            'user': user.to_dict(),
            'access_token': access_token,
            'refresh_token': refresh_token
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Ошибка входа: {str(e)}'}), 500


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Обновление access токена"""
    try:
        current_user_id = get_jwt_identity()
        access_token = create_access_token(identity=current_user_id)
        
        return jsonify({
            'access_token': access_token
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Ошибка обновления токена: {str(e)}'}), 500


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Получение информации о текущем пользователе с правами доступа"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'Пользователь не найден'}), 404
        
        return jsonify(user.to_dict()), 200
        
    except Exception as e:
        return jsonify({'error': f'Ошибка получения пользователя: {str(e)}'}), 500



