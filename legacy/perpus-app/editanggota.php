<?php
// Include your database connection file
include 'koneksi.php';

// Check if the connection is established
if (!$conn) {
    die("Connection failed: " . mysqli_connect_error());
}

// Check if ID is passed via GET parameter
if (!isset($_GET['id'])) {
    die("ID tidak ditemukan.");
}

// Retrieve member details from database
$id = $_GET['id'];
$query = "SELECT * FROM anggota WHERE id = $id";
$result = $conn->query($query);

if (!$result) {
    die("Error: " . $conn->error);
}

if ($result->num_rows > 0) {
    // Fetch data
    $row = $result->fetch_assoc();
    $nama = $row['nama'];
    $umur = $row['umur'];
    $alamat = $row['alamat'];
    $no_hp = $row['no_hp'];
} else {
    echo "Data anggota tidak ditemukan.";
}

// Close the connection
$conn->close();
?>

<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-QWTKZyjpPEjISv5WaRU9OFeRpok6YctnYmDr5pNlyT2bRjXh0JMhjY6hW+ALEwIH" crossorigin="anonymous">
    <title>Perpustakaan UMUM - Edit Anggota</title>
</head>

<body>
    <nav class="navbar navbar-expand-lg bg-body-tertiary">
        <div class="container-fluid">
            <img class="navbar-brand" src="plugins/img/th.jpeg" style="width: 80px;"></img>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarSupportedContent" aria-controls="navbarSupportedContent" aria-expanded="false" aria-label="Toggle navigation">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarSupportedContent">
                <ul class="navbar-nav me-auto mb-2 mb-lg-0">
                    <li class="nav-item">
                        <a class="nav-link" aria-current="page" href="index.php">Beranda</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="buku.php">Buku</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link active" href="anggota.php">Anggota</a>
                    </li>
                    <li class="nav-item dropdown">
                        <a class="nav-link dropdown-toggle" href="#" role="button" data-bs-toggle="dropdown" aria-expanded="false">
                            Transaksi
                        </a>
                        <ul class="dropdown-menu">
                            <li><a class="dropdown-item" href="#">Peminjaman</a></li>
                            <li><a class="dropdown-item" href="#">Pengembalian</a></li>
                        </ul>
                    </li>
                </ul>
            </div>
        </div>
    </nav>

    <div class="container">
        <main>
            <div class="container py-5">
                <div class="p-3 bg-body-tertiary rounded-3">
                    <div class="container-fluid">
                        <h1 class="display-6 fw-bold">Edit Anggota</h1>
                    </div>
                </div>

                <!-- Form Edit Anggota -->
                <div class="album py-5 bg-body-tertiary">
                    <div class="container">
                        <div class="col-md-7 col-lg-8">
                            <form class="needs-validation" novalidate action="proses_edit_anggota.php" method="post">
                                <input type="hidden" name="id" value="<?php echo $id; ?>">
                                <div class="row g-3">
                                    <div class="col-12">
                                        <label for="nama" class="form-label">Nama Anggota</label>
                                        <input type="text" class="form-control" id="nama" name="nama" value="<?php echo $nama; ?>" required>
                                        <div class="invalid-feedback">
                                            Masukkan Nama Anggota.
                                        </div>
                                    </div>

                                    <div class="col-12">
                                        <label for="umur" class="form-label">Umur</label>
                                        <input type="number" class="form-control" id="umur" name="umur" value="<?php echo $umur; ?>" required>
                                        <div class="invalid-feedback">
                                            Masukkan Umur.
                                        </div>
                                    </div>

                                    <div class="col-12">
                                        <label for="alamat" class="form-label">Alamat</label>
                                        <textarea class="form-control" id="alamat" name="alamat" required><?php echo $alamat; ?></textarea>
                                        <div class="invalid-feedback">
                                            Masukkan Alamat.
                                        </div>
                                    </div>

                                    <div class="col-12">
                                        <label for="no_hp" class="form-label">No HP</label>
                                        <input type="text" class="form-control" id="no_hp" name="no_hp" value="<?php echo $no_hp; ?>" required>
                                        <div class="invalid-feedback">
                                            Masukkan No HP.
                                        </div>
                                    </div>
                                </div>

                                <hr class="my-4">

                                <div class="btn-group d-flex justify-content-between align-items-center gap-4">
                                    <button class="w-100 btn btn-primary btn-lg" type="submit">Simpan Perubahan</button>
                                    <a href="anggota.php" class="w-100 btn btn-warning btn-lg">Batal</a>
                                </div>

                            </form>
                        </div>
                    </div>
                </div>
            </div>
        </main>
    </div>

    <!-- Script Boostrap -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js" integrity="sha384-YvpcrYf0tY3lHB60NNkmXc5s9fDVZLESaAA55NDzOxhy9GkcIdslK1eN7N6jIeHz" crossorigin="anonymous"></script>
</body>

</html>
