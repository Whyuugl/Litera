<?php
// Memeriksa apakah request merupakan POST atau GET dengan id
if ($_SERVER["REQUEST_METHOD"] == "POST" || isset($_GET['id'])) {
    // Mengambil id dari POST jika ada, jika tidak dari GET
    $id = isset($_POST['id']) ? $_POST['id'] : $_GET['id'];

    // Koneksi ke database (pastikan include koneksi.php sudah benar dan berfungsi)
    include '../koneksi.php';

    if ($conn) {
        // Query untuk delete data peminjaman berdasarkan id
        $sql = "DELETE FROM peminjaman WHERE id = ?";
        $stmt = $conn->prepare($sql);
        $stmt->bind_param("i", $id);

        // Mengeksekusi statement
        if ($stmt->execute()) {
            echo "<script>alert('Data peminjaman berhasil dihapus.'); window.location.href = '../peminjaman.php';</script>";
        } else {
            echo "<script>alert('Error: " . $stmt->error . "');</script>";
        }

        // Menutup statement
        $stmt->close();
    } else {
        echo "<script>alert('Koneksi ke database tidak berhasil.'); window.location.href = '../peminjaman.php';</script>";
    }

    // Menutup koneksi
    $conn->close();
} else {
    echo "<script>alert('Akses tidak sah.'); window.location.href = '../peminjaman.php';</script>";
}
?>
