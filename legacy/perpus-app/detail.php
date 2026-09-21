<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-QWTKZyjpPEjISv5WaRU9OFeRpok6YctnYmDr5pNlyT2bRjXh0JMhjY6hW+ALEwIH" crossorigin="anonymous">
    <title>Detail Buku - <?= $buku['nama_buku'] ?></title>
</head>

<?php
include 'koneksi.php';

if (!isset($_GET['id'])) {
    header("location: index.php");
    exit;
}

$id = $_GET['id'];

// Query untuk mendapatkan detail buku berdasarkan id
$sql = "SELECT * FROM buku WHERE id = ?";
$stmt = $conn->prepare($sql);
$stmt->bind_param("i", $id);
$stmt->execute();
$result = $stmt->get_result();
$buku = $result->fetch_assoc();

if (!$buku) {
    echo "Buku tidak ditemukan!";
    exit;
}
?>

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
                        <a class="nav-link active" href="buku.php">Buku</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="anggota.php">Anggota</a>
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
                        <h1 class="display-6 fw-bold">Detail Buku - <?= $buku['nama_buku'] ?></h1>
                    </div>
                </div>

                <!-- Koleksi Buku -->
                <div class="album py-2 bg-body-tertiary">
                    <div class="container">
                        <div class="card shadow-sm">
                            <div class="row featurette">
                                <div class="col-md-4 order-md-1">
                                    <img class="bd-placeholder-img bd-placeholder-img-lg featurette-image img-fluid mx-auto" width="500" height="500" src="<?= $buku['cover_buku'] ?>" role="img" preserveAspectRatio="xMidYMid slice" focusable="false">
                                    </img>
                                </div>
                                <div class="col-md-6 order-md-2">
                                    <p class="fs-5 fw-semibold text-primary mb-0">Judul Buku</p>
                                    <h5 class="mb-0 mt-0">
                                        <?= $buku['nama_buku'] ?>
                                    </h5>

                                    <hr>

                                    <p class="fs-5 fw-semibold text-primary mb-0">Sinopsis Buku</p>
                                    <p class="card-text">
                                        <?= $buku['sinopsis'] ?>
                                    </p>

                                    <hr>

                                    <p class="fs-5 fw-semibold text-primary mb-0">Penulis</p>
                                    <p class="card-text">
                                        <?= $buku['penulis'] ?>
                                    </p>

                                    <hr>

                                    <p class="fs-5 fw-semibold text-primary mb-0">Penerbit</p>
                                    <p class="card-text">
                                        <?= $buku['penerbit'] ?>
                                    </p>

                                    <p class="fs-5 fw-semibold text-primary mb-0">Tahun Terbit</p>
                                    <p class="card-text">
                                        <?= $buku['tahun_terbit'] ?>
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Footer -->
                <footer class="d-flex flex-wrap justify-content-between align-items-center py-3 my-4 border-top">
                    <p class="col-md-4 mb-0 text-body-secondary">&copy; 2024 Company, Inc</p>

                    <a href="/" class="col-md-4 d-flex align-items-center justify-content-center mb-3 mb-md-0 me-md-auto link-body-emphasis text-decoration-none">
                        <svg class="bi me-2" width="40" height="32">
                            <use xlink:href="#bootstrap" />
                        </svg>
                    </a>

                    <ul class="nav col-md-4 justify-content-end">
                        <li class="nav-item"><a href="#" class="nav-link px-2 text-body-secondary">Home</a></li>
                        <li class="nav-item"><a href="#" class="nav-link px-2 text-body-secondary">Features</a></li>
                        <li class="nav-item"><a href="#" class="nav-link px-2 text-body-secondary">Pricing</a></li>
                        <li class="nav-item"><a href="#" class="nav-link px-2 text-body-secondary">FAQs</a></li>
                        <li class="nav-item"><a href="#" class="nav-link px-2 text-body-secondary">About</a></li>
                    </ul>
                </footer>
            </div>
        </main>
    </div>

    <!-- Script Boostrap -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js" integrity="sha384-YvpcrYf0tY3lHB60NNkmXc5s9fDVZLESaAA55NDzOxhy9GkcIdslK1eN7N6jIeHz" crossorigin="anonymous"></script>
</body>

</html>