from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Company, User

companies_bp = Blueprint('companies', __name__)


@companies_bp.route('', methods=['GET'])
def get_companies():
    """Получение списка всех компаний"""
    try:
        companies = Company.query.all()
        return jsonify([company.to_dict() for company in companies]), 200
    except Exception as e:
        return jsonify({'error': f'Ошибка получения компаний: {str(e)}'}), 500


@companies_bp.route('/<string:company_id>', methods=['GET'])
def get_company(company_id):
    """Получение информации о конкретной компании"""
    try:
        company = Company.query.get(company_id)
        
        if not company:
            return jsonify({'error': 'Компания не найдена'}), 404
        
        # Получаем пользователей компании
        company_data = company.to_dict()
        company_data['users_count'] = len(company.users)
        
        return jsonify(company_data), 200
    except Exception as e:
        return jsonify({'error': f'Ошибка получения компании: {str(e)}'}), 500


@companies_bp.route('', methods=['POST', 'OPTIONS'])
def create_company():
    """Создание новой компании"""
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        data = request.get_json()
        
        # Валидация данных
        if not data or not data.get('name'):
            return jsonify({'error': 'Поле name обязательно'}), 400
        
        # Создание компании (UUID генерируется автоматически)
        company = Company(
            name=data['name'],
            description=data.get('description'),
            address=data.get('address'),
            phone=data.get('phone'),
            email=data.get('email')
        )
        
        db.session.add(company)
        db.session.commit()
        
        return jsonify({
            'message': 'Компания создана успешно',
            'company': company.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Ошибка создания компании: {str(e)}'}), 500


@companies_bp.route('/<string:company_id>', methods=['PUT'])
@jwt_required()
def update_company(company_id):
    """Обновление информации о компании"""
    try:
        company = Company.query.get(company_id)
        
        if not company:
            return jsonify({'error': 'Компания не найдена'}), 404
        
        data = request.get_json()
        
        # Обновление полей
        if 'name' in data:
            company.name = data['name']
        if 'description' in data:
            company.description = data['description']
        if 'address' in data:
            company.address = data['address']
        if 'phone' in data:
            company.phone = data['phone']
        if 'email' in data:
            company.email = data['email']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Компания обновлена успешно',
            'company': company.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Ошибка обновления компании: {str(e)}'}), 500


@companies_bp.route('/<string:company_id>', methods=['DELETE'])
@jwt_required()
def delete_company(company_id):
    """Удаление компании"""
    try:
        company = Company.query.get(company_id)
        
        if not company:
            return jsonify({'error': 'Компания не найдена'}), 404
        
        # Проверка, есть ли пользователи у компании
        if company.users:
            return jsonify({
                'error': 'Невозможно удалить компанию с пользователями',
                'users_count': len(company.users)
            }), 400
        
        db.session.delete(company)
        db.session.commit()
        
        return jsonify({'message': 'Компания удалена успешно'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Ошибка удаления компании: {str(e)}'}), 500


@companies_bp.route('/<string:company_id>/users', methods=['GET'])
def get_company_users(company_id):
    """Получение списка пользователей компании"""
    try:
        company = Company.query.get(company_id)
        
        if not company:
            return jsonify({'error': 'Компания не найдена'}), 404
        
        users = User.query.filter_by(parent_company_id=company_id).all()
        
        return jsonify({
            'company': company.to_dict(),
            'users': [user.to_dict() for user in users]
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Ошибка получения пользователей: {str(e)}'}), 500

