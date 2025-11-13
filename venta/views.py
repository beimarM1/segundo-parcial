from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import viewsets, status
from django.db import transaction
from django.conf import settings
import stripe
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Venta, DetalleVenta , Garantia
from .serializers import VentaSerializer, GarantiaSerializer
from producto.models import Producto
from users.models import CustomUser
from users.views import get_client_ip
from bitacora.models import Bitacora
from rest_framework.decorators import action
from datetime import timedelta
from django.utils import timezone
from dateutil.relativedelta import relativedelta  # Correcta importación de relativedelta
from datetime import datetime
from django.core.files.storage import FileSystemStorage

from rest_framework import permissions
from rest_framework.views import APIView
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO

# Configurar Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


# ✅ PROBAR CLAVE DE STRIPE
@api_view(['GET'])
def probar_stripe_key(request):
    return Response({"stripe_key_ok": bool(stripe.api_key)})


# 💳 CREAR INTENTO DE PAGO CON STRIPE
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def crear_pago(request):
    """
    Crea un PaymentIntent en Stripe y devuelve el client_secret
    que el frontend usará para confirmar el pago.
    """
    try:
        monto = request.data.get('monto')
        if not monto:
            return Response({'error': 'El monto es requerido.'}, status=status.HTTP_400_BAD_REQUEST)

        intent = stripe.PaymentIntent.create(
            amount=int(monto*100),  # en centavos (5000 = $50.00)
            currency='usd',
            payment_method_types=['card']
        )

        return Response({'client_secret': intent.client_secret}, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)








# 🧾 REGISTRAR VENTA (después de pago exitoso)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def registrar_venta(request):
    """
    Registra una venta y sus detalles, actualizando inventario.
    Se llama después de confirmar el pago exitoso.
    """
    print("📦 Datos recibidos: - views.py:79", request.data)  # Imprimir los datos recibidos

    try:
        usuario = request.user
        data = request.data
        productos = data.get('productos', [])
        total = data.get('total')

        if not productos or not total:
            print("❌ Falta productos o total. - views.py:88")
            return Response({'error': 'Debe enviar productos y total.'}, status=status.HTTP_400_BAD_REQUEST)

        # Crear la venta
        venta = Venta.objects.create(usuario=usuario, total=total, estado="pagado")
        print(f"✅ Venta creada: {venta.id}  Total: {venta.total} - views.py:93")

        # Crear los detalles
        for item in productos:
          #  try:
                producto = Producto.objects.get(id=item['producto_id'])
                cantidad = int(item['cantidad'])
                print(f"✔️ Producto encontrado: {producto.nombre}  Cantidad: {cantidad} - views.py:100")

                if producto.stock < cantidad:
                    print(f"❌ Stock insuficiente para {producto.nombre} - views.py:103")
                    raise ValueError(f"Stock insuficiente para {producto.nombre}")

                subtotal = producto.precio * cantidad

                DetalleVenta.objects.create(
                    venta=venta,
                    producto=producto,
                    cantidad=cantidad,
                    precio_unitario=producto.precio,
                    subtotal=subtotal,
                )
                print(f"✅ Detalle de venta registrado: Producto: {producto.nombre}  Subtotal: {subtotal} - views.py:115")

                # Establecer la fecha de inicio como la fecha de la venta
                fecha_inicio = datetime.today().date()
                print(f"📅 Fecha de inicio: {fecha_inicio} - views.py:119")

                # Verifica el valor de producto.garantia
                if hasattr(producto, 'garantia'):
                    print(f"🔑 Duración de la garantía en meses: {producto.garantia} - views.py:123")
                else:
                    print("❌ El producto no tiene un campo 'garantia' definido correctamente. - views.py:125")

                # Crear la garantía
                garantia = Garantia.objects.create(
                    producto=producto,
                    venta=venta,
                    fecha_fin=fecha_inicio + relativedelta(months=producto.garantia),

                    fecha_inicio=fecha_inicio,
                    estado='activa',
                )

                print(f"✅ Garantía creada: {producto.nombre}  Fecha de inicio: {garantia.fecha_inicio}  Fecha de fin: {garantia.fecha_fin} - views.py:137")

           # except Producto.DoesNotExist:
              #  print("❌ Producto no encontrado. - views.py:140")
             #   return Response({'error': 'Producto no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

           # except Exception as e:
               # print(f"❌ Error al procesar producto: {str(e)} - views.py:144")
                continue  # Continuar con el siguiente producto

            # Actualizar inventario
                producto.stock -= cantidad
                producto.save()
                print(f"🛒 Inventario actualizado: {producto.nombre}  Stock restante: {producto.stock} - views.py:150")
        
        
        
        # Crear la nota de venta en PDF
        pdf_buffer = generar_nota_venta(venta)

        # Guardar el PDF en el sistema de archivos
        fs = FileSystemStorage()
        file_name = f"nota_venta_{venta.id}.pdf"
        pdf_path = fs.save(file_name, pdf_buffer)

        
        # Registrar en bitácora
        Bitacora.objects.create(
            usuario=usuario,
            accion=f"Registró venta #{venta.id} por un total de {venta.total} USD",
            ip=get_client_ip(request),
            estado=True,
        )
        print(f"✅ Venta registrada en la bitácora: Venta #{venta.id} - views.py:170")

        return Response({
            'mensaje': '✅ Venta registrada con éxito.',
            'venta': VentaSerializer(venta).data,
            'nota_venta': fs.url(pdf_path)  # URL para acceder al archivo PDF  
        }, status=status.HTTP_201_CREATED)

    except CustomUser.DoesNotExist:
        print("❌ Cliente no encontrado. - views.py:179")
        return Response({'error': 'Cliente no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        print(f"❌ Error general: {str(e)} - views.py:183")
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)







# 📋 LISTAR TODAS LAS VENTAS
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def listar_ventas(request):
    """
    Lista todas las ventas registradas.
    Si el usuario no es admin, solo ve sus propias ventas.
    """
    try:
        usuario = request.user

        # Si el usuario es admin, ve todas las ventas
        if usuario.is_staff or usuario.is_superuser:
            ventas = Venta.objects.all().order_by('-id')
        else:
            ventas = Venta.objects.filter(usuario=usuario).order_by('-id')

        serializer = VentaSerializer(ventas, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)






# 🔍 OBTENER DETALLE DE UNA VENTA
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_venta(request, venta_id):
    """
    Devuelve los detalles de una venta específica.
    """
    try:
        venta = Venta.objects.get(id=venta_id)

        # Solo el usuario dueño o un admin puede verla
        if not (request.user.is_staff or request.user.is_superuser or venta.usuario == request.user):
            return Response({'error': 'No tiene permisos para ver esta venta.'},
                            status=status.HTTP_403_FORBIDDEN)

        serializer = VentaSerializer(venta)
        return Response(serializer.data, status=status.HTTP_200_OK)

    except Venta.DoesNotExist:
        return Response({'error': 'Venta no encontrada.'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

















# ✏️ EDITAR (ACTUALIZAR) UNA VENTA
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def editar_venta(request, venta_id):
    """
    Permite modificar el estado o detalles de una venta.
    Generalmente para actualizar estado (ej: entregado, cancelado, etc.)
    """
    try:
        venta = Venta.objects.get(id=venta_id)

        # ✅ Debug info: qué usuario hace la petición
        print("🧑‍💼 Usuario autenticado: - views.py:272", request.user.email if hasattr(request.user, 'email') else request.user)
        print("🧾 ID de la venta recibida: - views.py:273", venta_id)
        print("📩 Datos recibidos en el request: - views.py:274", request.data)

        # Solo admin o el creador puede editar
        if not (request.user.is_staff or request.user.is_superuser or venta.usuario == request.user):
            print("⛔ Permiso denegado al usuario: - views.py:278", request.user)
            return Response({'error': 'No tiene permisos para editar esta venta.'},
                            status=status.HTTP_403_FORBIDDEN)

        serializer = VentaSerializer(venta, data=request.data, partial=True)

        if serializer.is_valid():
            print("✅ Datos validados correctamente. Campos válidos: - views.py:285", serializer.validated_data)
            serializer.save()
            print("💾 Venta actualizada exitosamente en BD. - views.py:287")

            # Registrar en bitácora
            Bitacora.objects.create(
                usuario=request.user,
                accion=f"Editó la venta #{venta.id}",
                ip=get_client_ip(request),
                estado=True,
            )

            return Response({
                'mensaje': '✅ Venta actualizada correctamente.',
                'venta': serializer.data
            }, status=status.HTTP_200_OK)

        else:
            print("⚠️ Error de validación en serializer: - views.py:303", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    except Venta.DoesNotExist:
        print("❌ Venta no encontrada con ID: - views.py:307", venta_id)
        return Response({'error': 'Venta no encontrada.'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        print("💣 Error inesperado al editar venta: - views.py:310", str(e))
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)



class OrdersPageView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # Obtener todas las ventas del usuario autenticado
        user = request.user  # El usuario autenticado
        orders = Venta.objects.filter(usuario=user)  # Filtrar las órdenes por el usuario autenticado
        
        # Serializar las órdenes
        serializer = VentaSerializer(orders, many=True)

        return Response(serializer.data, status=200)
    









@api_view(['GET'])
@permission_classes([AllowAny])
def obtener_garantias_por_venta(request, venta_id):
    """
    Devuelve las garantías asociadas a una venta específica.
    """
    try:
        venta = Venta.objects.get(id=venta_id)

        # Solo el usuario dueño de la venta o un admin puede ver las garantías de esa venta
        if not (request.user.is_staff or request.user.is_superuser or venta.usuario == request.user):
            return Response({'error': 'No tiene permisos para ver las garantías de esta venta.'},
                            status=status.HTTP_403_FORBIDDEN)

        # Obtiene las garantías asociadas a la venta
        garantias = Garantia.objects.filter(venta=venta)

        if not garantias.exists():
            return Response({'error': 'No se encontraron garantías para esta venta.'}, 
                            status=status.HTTP_404_NOT_FOUND)

        # Serializa las garantías
        serializer = GarantiaSerializer(garantias, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    except Venta.DoesNotExist:
        return Response({'error': 'Venta no encontrada.'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)








# Función para generar el PDF de la nota de venta
def generar_nota_venta(venta):
    buffer = BytesIO()

    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter  # Definir tamaño de página (carta)

    # Título
    c.setFont("Helvetica-Bold", 16)
    c.drawString(30, height - 40, f"Nota de Venta #{venta.id}")

    # Detalles de la venta
    c.setFont("Helvetica", 12)
    c.drawString(30, height - 60, f"Fecha: {venta.fecha}")
    c.drawString(30, height - 80, f"Cliente: {venta.usuario.username}")
    c.drawString(30, height - 100, f"Total: {venta.total} USD")

    # Detalle de los productos
    y_position = height - 140
    c.drawString(30, y_position, "Productos:")
    y_position -= 20

    for detalle in venta.detalles.all():
        producto = detalle.producto
        c.drawString(30, y_position, f"{producto.nombre} - Cantidad: {detalle.cantidad} - Subtotal: {detalle.subtotal}")
        y_position -= 20

    # Finalizar el PDF
    c.showPage()
    c.save()

    # Regresar el archivo PDF generado
    buffer.seek(0)
    return buffer