<?php
include '../koneksi.php';

if (isset($_POST['id'])) {
    $id = $_POST['id'];

    // Ambil data dari tabel peminjaman
    $sql = "SELECT nama_peminjam, nama_buku FROM peminjaman WHERE id = ?";
    $stmt = $conn->prepare($sql);
    $stmt->bind_param("i", $id);
    $stmt->execute();
    $result = $stmt->get_result();
    $row = $result->fetch_assoc();

    if ($row) {
        // Insert data ke tabel pengembalian
        $nama_peminjam = $row['nama_peminjam'];
        $nama_buku = $row['nama_buku'];
        $tanggal_pengembalian = date('Y-m-d'); // Tanggal pengembalian saat ini

        $sql_insert = "INSERT INTO pengembalian (nama_peminjam, nama_buku, tanggal_pengembalian) VALUES (?, ?, ?)";
        $stmt_insert = $conn->prepare($sql_insert);
        $stmt_insert->bind_param("sss", $nama_peminjam, $nama_buku, $tanggal_pengembalian);
        $stmt_insert->execute();

        // Hapus data dari tabel peminjaman
        $sql_delete = "DELETE FROM peminjaman WHERE id = ?";
        $stmt_delete = $conn->prepare($sql_delete);
        $stmt_delete->bind_param("i", $id);
        $stmt_delete->execute();

        // Redirect kembali ke halaman peminjaman
        header("Location: ../pengembalian.php");
    } else {
        echo "Data peminjaman tidak ditemukan.";
    }
} else {
    echo "ID tidak diberikan.";
}

$conn->close();
?>
