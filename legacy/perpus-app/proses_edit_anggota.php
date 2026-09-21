<?php
// Include your database connection file
include 'koneksi.php';

// Check if the connection is established
if (!$conn) {
    die("Connection failed: " . mysqli_connect_error());
}

// Check if form submission has data
if ($_SERVER["REQUEST_METHOD"] == "POST") {
    // Collect form data
    $id = $_POST['id'];
    $nama = $_POST['nama'];
    $umur = $_POST['umur'];
    $alamat = $_POST['alamat'];
    $no_hp = $_POST['no_hp'];

    // Prepare an update statement
    $sql = "UPDATE anggota SET nama='$nama', umur='$umur', alamat='$alamat', no_hp='$no_hp' WHERE id='$id'";

    // Execute the update statement
    if ($conn->query($sql) === TRUE) {
        header("Location: anggota.php");
    exit();
    } else {
        echo "Error updating record: " . $conn->error;
    }
}

// Close the database connection
$conn->close();
?>
