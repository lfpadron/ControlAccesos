import 'dart:typed_data';

import 'package:pdf/pdf.dart';
import 'package:pdf/widgets.dart' as pw;
import 'package:printing/printing.dart';

import 'models.dart';

Future<Uint8List> buildTicketPdf(TicketResponse ticket) async {
  final document = pw.Document();
  const pageFormat = PdfPageFormat(80 * PdfPageFormat.mm, 180 * PdfPageFormat.mm, marginAll: 5 * PdfPageFormat.mm);

  document.addPage(
    pw.Page(
      pageFormat: pageFormat,
      build: (context) {
        return pw.Center(
          child: pw.Column(
            mainAxisSize: pw.MainAxisSize.min,
            crossAxisAlignment: pw.CrossAxisAlignment.center,
            children: [
              pw.Text(ticket.encabezadoFecha, style: pw.TextStyle(fontSize: 12, fontWeight: pw.FontWeight.bold)),
              pw.SizedBox(height: 4),
              pw.Text(ticket.leyenda, style: const pw.TextStyle(fontSize: 10)),
              pw.Divider(),
              pw.Text('TURNO', style: const pw.TextStyle(fontSize: 10)),
              pw.Text(ticket.turno, style: pw.TextStyle(fontSize: 34, fontWeight: pw.FontWeight.bold)),
              pw.SizedBox(height: 6),
              pw.Text(ticket.consultorio, textAlign: pw.TextAlign.center, style: const pw.TextStyle(fontSize: 13)),
              pw.Text(ticket.piso, textAlign: pw.TextAlign.center, style: const pw.TextStyle(fontSize: 11)),
              pw.Text('Hora ${ticket.hora}', style: const pw.TextStyle(fontSize: 11)),
              pw.SizedBox(height: 10),
              pw.BarcodeWidget(
                barcode: pw.Barcode.qrCode(),
                data: ticket.qrPayload,
                width: 105,
                height: 105,
              ),
              pw.SizedBox(height: 8),
              pw.Text('Conserve este ticket para su llamado.', textAlign: pw.TextAlign.center, style: const pw.TextStyle(fontSize: 9)),
            ],
          ),
        );
      },
    ),
  );

  return document.save();
}

Future<void> printTicketPdf(TicketResponse ticket) async {
  final bytes = await buildTicketPdf(ticket);
  await Printing.layoutPdf(
    name: 'ticket_${ticket.turno}.pdf',
    onLayout: (_) async => bytes,
  );
}
