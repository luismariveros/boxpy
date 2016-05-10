$(document).ready(function() {
    $('#tablaFull').dataTable({
        "bDestroy": true,
        "oLanguage": {
            "sSearch": "Buscar: ",
            "sLengthMenu": "Mostrar _MENU_ registros por página",
            "sZeroRecords": "No hay resultado",
            "sInfo": "_START_ de _END_ (_TOTAL_ registros)",
            "sInfoEmpty": "0 de 0 (0 registro)",
            "sInfoFiltered": "(filtered from _MAX_ total records)",
            "oPaginate": {
                "sFirst": "Primera Pág.",
                "sLast": "Última Pág.",
                "sPrevious": "Anterior",
                "sNext": "Siguiente"
            }
        }
    });
});