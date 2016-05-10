// Configuraciones Generales
var nombre_tabla = "#tabla_compras"; // id
var nombre_boton_eliminar = ".delete"; // Clase
var nombre_formulario_modal = "#frmEliminarCompra"; //id
var nombre_ventana_modal = "#myModal"; // id
// Fin de configuraciones


    $(document).on('ready',function(){
        $(nombre_boton_eliminar).on('click',function(e){
            e.preventDefault();
            var Cid = $(this).attr('id');
            var name = $(this).data('name');
            var username = $(this).data('user');
            $('#modal_idCompra').val(Cid);
            $('#modal_name').text(name);
            $('#modal_user').text(username)
        });

        var options = {
            success:function(response)
            {
                if(response.status=="True"){
                    var idCompra= response.compra_id;
                    var elementos= $(nombre_tabla+' >tbody >tr').length;
                    if(elementos==1){
                            location.reload();
                    }else{
                        $('#tr'+idCompra).remove();
                        $(nombre_ventana_modal).modal('hide');
                    }

                }else{
                    alert("Hubo un error al eliminar!");
                    $(nombre_ventana_modal).modal('hide');
                };
            }
        };

        $(nombre_formulario_modal).ajaxForm(options);
    });
