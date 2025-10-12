from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import uuid

db = SQLAlchemy()


def generate_uuid():
    """Генерирует UUID строку"""
    return str(uuid.uuid4())


class Company(db.Model):
    """Модель компании"""
    __tablename__ = 'companies'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    address = db.Column(db.String(255))
    phone = db.Column(db.String(50))
    email = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связь с пользователями
    users = db.relationship('User', backref='company', lazy=True)
    
    def to_dict(self):
        """Преобразует модель в словарь"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'address': self.address,
            'phone': self.phone,
            'email': self.email,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class User(db.Model):
    """Модель пользователя"""
    __tablename__ = 'users'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    email = db.Column(db.String(120), unique=True, nullable=False)  # email используется как username
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='user')  # user, admin
    parent_company_id = db.Column(db.String(36), db.ForeignKey('companies.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def set_password(self, password):
        """Устанавливает хэш пароля"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Проверяет пароль"""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        """Преобразует модель в словарь"""
        return {
            'id': self.id,
            'email': self.email,
            'role': self.role,
            'parent_company_id': self.parent_company_id,
            'company': self.company.to_dict() if self.company else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class Location(db.Model):
    """Модель площадки для сбора мусора"""
    __tablename__ = 'locations'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    lat = db.Column(db.Float, nullable=False)
    lng = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='empty')  # empty, partial, full
    company_id = db.Column(db.String(36), db.ForeignKey('companies.id'), nullable=True)
    last_collection = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи
    containers = db.relationship('Container', backref='location', lazy=True, cascade='all, delete-orphan')
    company = db.relationship('Company', backref='locations')
    
    def update_status(self):
        """Обновляет статус площадки на основе контейнеров"""
        if not self.containers:
            self.status = 'empty'
            return
        
        statuses = [c.status for c in self.containers]
        if all(s == 'full' for s in statuses):
            self.status = 'full'
        elif all(s == 'empty' for s in statuses):
            self.status = 'empty'
        else:
            self.status = 'partial'
    
    def to_dict(self):
        """Преобразует модель в словарь"""
        return {
            'id': self.id,
            'name': self.name,
            'address': self.address,
            'lat': self.lat,
            'lng': self.lng,
            'status': self.status,
            'company_id': self.company_id,
            'company': self.company.to_dict() if self.company else None,
            'lastCollection': self.last_collection.strftime('%d.%m.%Y, %H:%M') if self.last_collection else None,
            'containers': [c.to_dict() for c in self.containers],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class Container(db.Model):
    """Модель контейнера для мусора"""
    __tablename__ = 'containers'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    location_id = db.Column(db.String(36), db.ForeignKey('locations.id'), nullable=False)
    number = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='empty')  # empty, partial, full
    fill_level = db.Column(db.Integer, default=0)  # 0-100%
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Преобразует модель в словарь"""
        return {
            'id': self.id,
            'number': self.number,
            'status': self.status,
            'fill_level': self.fill_level
        }


class Collection(db.Model):
    """Модель записи о сборе мусора"""
    __tablename__ = 'collections'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    location_id = db.Column(db.String(36), db.ForeignKey('locations.id'), nullable=False)
    collected_at = db.Column(db.DateTime, default=datetime.utcnow)
    containers_count = db.Column(db.Integer, default=0)
    notes = db.Column(db.Text)
    collected_by = db.Column(db.String(36), db.ForeignKey('users.id'))
    
    # Связи
    location = db.relationship('Location', backref='collections')
    user = db.relationship('User', backref='collections')
    
    def to_dict(self):
        """Преобразует модель в словарь"""
        return {
            'id': self.id,
            'location_id': self.location_id,
            'location_name': self.location.name if self.location else None,
            'collected_at': self.collected_at.isoformat() if self.collected_at else None,
            'containers_count': self.containers_count,
            'notes': self.notes,
            'collected_by': self.user.email if self.user else None
        }

