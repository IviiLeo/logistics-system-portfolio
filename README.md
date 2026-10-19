# Architecture Decision Record (ADR) & System Design - Sprint 1
## Sistema Backend para Gestión Logística, Orquestación de Rutas y Conciliación de Pagos

### 1. Decisiones de Arquitectura de Negocio (El Back-End Logístico)
Se optó por una estructura modular dividida en 4 aplicaciones Django exclusivas, priorizando la separación de responsabilidades (*Separation of Concerns*) y evitando la proliferación innecesaria de aplicaciones (*App Proliferation*).

#### 1.1. Las 4 Aplicaciones Core
1. **empleados:** Gestión de identidad, roles, permisos y control de sesiones. *(Completada)*
2. **pedidos:** Mantenimiento del catálogo, carga de paquetes y registro del ciclo de vida del pedido.
3. **hojas:** Agrupación de pedidos, asignación de choferes, gestión de rutas y evento de confirmación en puerta.
4. **pagos:** Registro de transacciones financieras, cuentas corrientes y validación administrativa.

*Decisión clave:* Se descartó explícitamente la creación de una app "entregas" independiente. La lógica operativa física se absorbió dentro de la app `hojas`, mientras que la lógica financiera se delegó a `pagos`. Esta decisión previene una arquitectura frágil y sobreacoplada.

#### 1.2. Diseño Relacional y Casos de Borde (Edge Cases)

**A. El Modelo de "Canasta" (Entidad Entrega)**
La entidad `Entrega` se aloja en la app `hojas`. Actúa estrictamente como el evento de agrupamiento físico que ocurre en la puerta del domicilio, vinculando múltiples pedidos como una entrega única en un instante de tiempo específico.

**B. Resolución de la Integridad Financiera ("Pagos Huérfanos")**
Para proteger la contabilidad ante fallos logísticos en la calle, el modelo `Pago` se conecta directamente al modelo `Pedido` mediante una relación de muchos a muchos (`ManyToManyField`).
* **Resultado:** Si una entrega física fracasa y la Entrega nunca se consolida, el pago ingresado previamente sobrevive en el sistema como un **"Pago Huérfano"** asociado al pedido rebotado, permitiendo su posterior conciliación o devolución en la oficina.

**C. Manejo del Estado Sucio (Usuario Arrepentido)**
Para evitar relaciones transaccionales residuales si el transportista modifica el carrito en la puerta tras haber ingresado un pago, se implementó el uso del método `.set()` del ORM de Django en el endpoint de confirmación. Esto limpia automáticamente las relaciones antiguas y asigna el pago únicamente a los pedidos finalmente entregados (o no entregados) mas no a los pedidos aún pendientes.

**D. Manejo de Saldos a Favor (Sobrepagos)**
Ante sobrepagos causados por cambios de último minuto (por ejemplo, cuando el cliente abona el total pero rechaza un paquete en el momento de la entrega):
* La **App Móvil** asume la validación matemática primaria, alertando al usuario sobre la diferencia.
* El **Back-End** registra el pago completo para garantizar el arqueo de caja.
* La resolución (emisión de notas de crédito o reembolsos) se gestiona de forma administrativa offline a través de la trazabilidad expuesta en el panel de control.

#### 1.3. Diseño de Vistas Relacionales (ORM)
La arquitectura relacional diseñada permite consultas fluidas y bidireccionales sin redundancia de datos:
* **Desde un Pedido:** Acceso inmediato a los pagos asociados (incluyendo adelantos y pagos huérfanos). Consulta de pedidos conjuntos entregados en el mismo evento (a través de la entidad Entrega).
* **Desde un Pago:** Acceso directo a los pedidos específicos que cubre la transacción. Visibilidad de otros métodos de pago utilizados simultáneamente en la misma parada.

---

### 2. Estado de Implementación por Módulos

#### 2.1. App "empleados" (Identidad y Accesos) - Completado
* **Esquema Relacional, Encriptación y Validaciones Estrictas:** Creación de las entidades `Persona`, `Administrativo` y `Transportista`. Se implementó encriptación de contraseñas nativa (algoritmo PBKDF2 mediante `make_password` y `check_password`) sobrescribiendo el método `save()`, garantizando un almacenamiento seguro (*zero plaintext*). Se aplicaron validadores de expresiones regulares (Regex) a nivel modelo para asegurar la longitud y formato estricto de campos numéricos críticos (DNI, CBU).
* **Enrutamiento Dual y Feedback de UI (Web):** Desarrollo de la lógica completa de login/logout. Se configuró un sistema de URLs para vistas HTML nativas y se implementó el framework `messages.error` de Django para capturar excepciones en la lógica de solicitudes (ej. credenciales inválidas) y renderizar alertas de error precisas directamente en el front-end.
* **Políticas de Seguridad y Sesiones (`request.session`):** Configuración de protección activa de cuentas mediante la validación de `request.session` y *cookies*. Se establecieron políticas estrictas de caducidad: destrucción automática al cerrar el navegador o tras alcanzar un *Time-To-Live* (TTL) de 1 hora de inactividad.
* **Control de Accesos (RBAC) mediante Patrones de Diseño:** Desarrollo de decoradores de validación de estado inyectados en el enrutamiento web (*Decorator Pattern*). Estos interceptores verifican la validez de la sesión en cada página de la web y administran los "Permisos Ejecutivos", bloqueando funcionalidades críticas según el perfil.
* **Integración Backend-to-Mobile (API REST):** Exposición de endpoints de autenticación para la aplicación móvil (Expo) mediante su propio set de URLs. Lógica de verificación segura de credenciales en base de datos, delegando el cierre de sesión a la arquitectura *client-side*.

#### 2.2. App "hojas" (Rutas y Ejecución en Calle) - En Progreso
*(Sección reservada para documentar modelos HojaDeRuta, Entrega y la lógica de endpoints móviles en los próximos días).*

#### 2.3. App "pedidos" (Catálogo de Mercadería) - En Progreso
*(Sección reservada para documentar el CRUD de paquetes y sus cambios de estado).*

#### 2.4. App "pagos" (Conciliación Financiera) - Pendiente
*(Sección reservada para documentar la validación administrativa de transferencias y pagos huérfanos).*
