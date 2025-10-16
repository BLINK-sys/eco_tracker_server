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


class Role(db.Model):
    """Модель роли пользователя"""
    __tablename__ = 'roles'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    name = db.Column(db.String(50), unique=True, nullable=False)  # Владелец, Оператор
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи
    users = db.relationship('User', backref='role_obj')
    
    def to_dict(self):
        """Преобразует модель в словарь"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class AccessRight(db.Model):
    """Модель прав доступа для ролей"""
    __tablename__ = 'access_rights'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    
    # Права на страницы
    can_view_monitoring = db.Column(db.Boolean, default=False)
    can_view_notifications = db.Column(db.Boolean, default=False)
    can_view_locations = db.Column(db.Boolean, default=False)
    can_view_reports = db.Column(db.Boolean, default=False)
    can_view_admin = db.Column(db.Boolean, default=False)
    
    # Права в администрировании
    can_manage_users = db.Column(db.Boolean, default=False)
    can_manage_companies = db.Column(db.Boolean, default=False)
    can_view_security = db.Column(db.Boolean, default=False)
    can_manage_notifications = db.Column(db.Boolean, default=False)
    
    # Права на управление площадками
    can_create_locations = db.Column(db.Boolean, default=False)
    can_edit_locations = db.Column(db.Boolean, default=False)
    can_delete_locations = db.Column(db.Boolean, default=False)
    
    # Права на управление контейнерами
    can_create_containers = db.Column(db.Boolean, default=False)
    can_edit_containers = db.Column(db.Boolean, default=False)
    can_delete_containers = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Преобразует модель в словарь"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'can_view_monitoring': self.can_view_monitoring,
            'can_view_notifications': self.can_view_notifications,
            'can_view_locations': self.can_view_locations,
            'can_view_reports': self.can_view_reports,
            'can_view_admin': self.can_view_admin,
            'can_manage_users': self.can_manage_users,
            'can_manage_companies': self.can_manage_companies,
            'can_view_security': self.can_view_security,
            'can_manage_notifications': self.can_manage_notifications,
            'can_create_locations': self.can_create_locations,
            'can_edit_locations': self.can_edit_locations,
            'can_delete_locations': self.can_delete_locations,
            'can_create_containers': self.can_create_containers,
            'can_edit_containers': self.can_edit_containers,
            'can_delete_containers': self.can_delete_containers,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class User(db.Model):
    """Модель пользователя"""
    __tablename__ = 'users'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    email = db.Column(db.String(120), unique=True, nullable=False)  # email используется как username
    password_hash = db.Column(db.String(255), nullable=False)
    role_id = db.Column(db.String(36), db.ForeignKey('roles.id'), nullable=False)  # Связь с ролями
    parent_company_id = db.Column(db.String(36), db.ForeignKey('companies.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи (company и role_obj уже определены через backref в соответствующих моделях)
    access_rights = db.relationship('AccessRight', backref='user', cascade='all, delete-orphan')
    
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
            'role': self.role_obj.name if self.role_obj else None,  # Получаем название роли из связанного объекта
            'role_id': self.role_id,
            'parent_company_id': self.parent_company_id,
            'company': self.company.to_dict() if self.company else None,
            'role_obj': self.role_obj.to_dict() if self.role_obj else None,
            'access_rights': [right.to_dict() for right in self.access_rights] if self.access_rights else [],
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
        print(f"[DEBUG] update_status called for location {self.id if hasattr(self, 'id') else 'UNKNOWN'} - NEW VERSION v2")
        try:
            # Сохраняем ID до любых операций с сессией
            location_id = self.id
            
            # Получаем свежую копию location из текущей сессии
            # Это гарантирует что мы работаем с объектом в активной сессии
            location_in_session = db.session.query(Location).filter_by(id=location_id).first()
            
            if not location_in_session:
                # Если location не найден, ничего не делаем
                return
            
            # Получаем контейнеры через явный запрос (без lazy load)
            containers = db.session.query(Container).filter(
                Container.location_id == location_id
            ).all()
            
            if not containers:
                location_in_session.status = 'empty'
                return
            
            # Определяем статус на основе контейнеров
            statuses = [c.status for c in containers]
            if all(s == 'full' for s in statuses):
                new_status = 'full'
            elif all(s == 'empty' for s in statuses):
                new_status = 'empty'
            else:
                new_status = 'partial'
            
            # Обновляем статус в объекте сессии
            location_in_session.status = new_status
            
            # Если self - это тот же объект (в сессии), обновляем и его
            if self in db.session:
                self.status = new_status
                
        except Exception as e:
            # Логируем ошибку, но не прерываем выполнение
            import logging
            logger = logging.getLogger(__name__)
            try:
                logger.error(f'Error in update_status for location {self.id}: {str(e)}')
            except:
                logger.error(f'Error in update_status: {str(e)}')
    
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


class FCMToken(db.Model):
    """Модель FCM токенов для мобильных уведомлений"""
    __tablename__ = 'fcm_tokens'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    token = db.Column(db.String(255), unique=True, nullable=False)
    device_info = db.Column(db.String(255))  # Информация об устройстве (опционально)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связь с пользователем
    user = db.relationship('User', backref=db.backref('fcm_tokens', lazy=True))
    
    def to_dict(self):
        """Преобразует модель в словарь"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'token': self.token,
            'device_info': self.device_info,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

