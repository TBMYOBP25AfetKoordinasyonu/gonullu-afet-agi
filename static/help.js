document.addEventListener("DOMContentLoaded", function () {
  // Form elemanlarını seç
  const helpForm = document.getElementById("helpForm");
  const disasterType = document.getElementById("disasterType");
  const latInput = document.getElementById("lat");
  const lngInput = document.getElementById("lng");
  const getLocationButton = document.getElementById("getLocationButton");
  const manualLocation = document.getElementById("manualLocation");
  const provinceSelect = document.getElementById("province");
  const districtSelect = document.getElementById("district");
  const neighborhoodSelect = document.getElementById("neighborhood");
  const streetSelect = document.getElementById("street");
  const manualLocationButton = document.getElementById("manualLocationButton");

  // Konum al butonuna tıklandığında otomatik konum al
  getLocationButton.addEventListener("click", getLocation);

  function getLocation() {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        function (position) {
          const lat = position.coords.latitude;
          const lng = position.coords.longitude;
          latInput.value = lat;
          lngInput.value = lng;
          console.log("Konum alındı:", lat, lng);
          manualLocation.style.display = "none";
        },
        function (error) {
          console.error("Geolocation error:", error);
          showManualLocation();
        }
      );
    } else {
      console.error("Geolocation bu tarayıcıda desteklenmiyor.");
      getLocationButton.style.display = "none";
      showManualLocation();
    }
  }

  manualLocationButton.addEventListener("click", showManualLocation);

  function showManualLocation() {
    if (latInput.value && lngInput.value) {
      alert("Konum alındığı için manuel konum almanıza gerek yok.");
      return;
    }
    manualLocation.style.display = "block";

    // Manuel form elemanlarına required özelliği ekle
    const requiredElements = manualLocation.querySelectorAll("select");
    requiredElements.forEach((element) => (element.required = true));

    // Şehir seçeneğini doldur
    fetch("static/data/provinces.json")
      .then((response) => {
        if (!response.ok) throw new Error("Şehir listesi yüklenemedi");
        return response.json();
      })
      .then((data) => {
        provinceSelect.innerHTML =
          '<option value="">Şehir seçiniz</option>' +
          data
            .map(
              (province) =>
                `<option value="${province.id}">${province.name}</option>`
            )
            .join("");
      })
      .catch((error) => {
        console.error("Şehir listesi yüklenirken hata:", error);
        provinceSelect.innerHTML =
          '<option value="">Şehir listesi yüklenemedi</option>';
      });
  }

  // Şehir seçildiğinde ilçe seçeneğini doldur
  provinceSelect.addEventListener("change", function () {
    const selectedCityId = this.value;
    if (!selectedCityId) {
      districtSelect.innerHTML = '<option value="">İlçe seçiniz</option>';
      neighborhoodSelect.innerHTML =
        '<option value="">Mahalle seçiniz</option>';
      streetSelect.innerHTML = '<option value="">Sokak seçiniz</option>';
      return;
    }

    fetch(`static/data/districts.json?cityId=${selectedCityId}`)
      .then((response) => {
        if (!response.ok) throw new Error("İlçe listesi yüklenemedi");
        return response.json();
      })
      .then((data) => {
        const filteredDistricts = data.filter(
          (district) => district.province_id === parseInt(selectedCityId)
        );
        districtSelect.innerHTML =
          '<option value="">İlçe seçiniz</option>' +
          filteredDistricts
            .map(
              (district) =>
                `<option value="${district.district_id}">${district.district_name}</option>`
            )
            .join("");
      })
      .catch((error) => {
        console.error("İlçe listesi yüklenirken hata:", error);
        districtSelect.innerHTML =
          '<option value="">İlçe listesi yüklenemedi</option>';
      });
  });

  // İlçe seçildiğinde mahalle seçeneğini doldur
  districtSelect.addEventListener("change", function () {
    const selectedDistrictId = this.value;
    if (!selectedDistrictId) {
      neighborhoodSelect.innerHTML =
        '<option value="">Mahalle seçiniz</option>';
      streetSelect.innerHTML = '<option value="">Sokak seçiniz</option>';
      return;
    }

    fetch(`static/data/neighborhoods.json?districtId=${selectedDistrictId}`)
      .then((response) => {
        if (!response.ok) throw new Error("Mahalle listesi yüklenemedi");
        return response.json();
      })
      .then((data) => {
        const filteredNeighborhoods = data.filter(
          (neighborhood) =>
            neighborhood.district_id === parseInt(selectedDistrictId)
        );
        neighborhoodSelect.innerHTML =
          '<option value="">Mahalle seçiniz</option>' +
          filteredNeighborhoods
            .map(
              (neighborhood) =>
                `<option value="${neighborhood.neighborhood_id}">${neighborhood.neighborhood_name}</option>`
            )
            .join("");
      })
      .catch((error) => {
        console.error("Mahalle listesi yüklenirken hata:", error);
        neighborhoodSelect.innerHTML =
          '<option value="">Mahalle listesi yüklenemedi</option>';
      });
  });

  // Mahalle seçildiğinde sokak seçeneğini doldur
  neighborhoodSelect.addEventListener("change", function () {
    const selectedNeighborhoodId = this.value;
    if (!selectedNeighborhoodId) {
      streetSelect.innerHTML = '<option value="">Sokak seçiniz</option>';
      return;
    }

    loadStreets(selectedNeighborhoodId);
  });

  // Form gönderimi
  helpForm.addEventListener("submit", async function (event) {
    event.preventDefault();

    // Afet türü kontrolü
    if (!disasterType.value) {
      alert("Lütfen bir afet türü seçiniz.");
      return;
    }

    // Konum kontrolü - lat ve lng alanları doluysa devam et
    if (!latInput.value || !lngInput.value) {
      if (
        !provinceSelect.value ||
        !districtSelect.value ||
        !neighborhoodSelect.value ||
        !streetSelect.value
      ) {
        alert(
          "Lütfen tüm konum bilgilerini doldurun (Şehir, İlçe, Mahalle ve Sokak)."
        );
        return;
      }

      try {
        const city = provinceSelect.options[provinceSelect.selectedIndex].text;
        const district =
          districtSelect.options[districtSelect.selectedIndex].text;
        const neighborhood =
          neighborhoodSelect.options[neighborhoodSelect.selectedIndex].text;
        const street = streetSelect.options[streetSelect.selectedIndex].text;

        const manualLocationData = [
          street !== "Sokak seçiniz" ? street : "",
          neighborhood !== "Mahalle seçiniz" ? neighborhood : "",
          district !== "İlçe seçiniz" ? district : "",
          city !== "Şehir seçiniz" ? city : "",
          "Türkiye",
        ]
          .filter(Boolean)
          .join(", ");

        console.log("Gönderilen adres:", manualLocationData);

        const response = await fetch(
          `https://api.geoapify.com/v1/geocode/search?text=${encodeURIComponent(
            manualLocationData
          )}&apiKey=6fa504a35adb49c0b9a746a5de07e68d&country=Türkiye&limit=1`
        );

        if (!response.ok) {
          throw new Error("Konum bilgisi alınamadı");
        }

        const data = await response.json();
        console.log("API Yanıtı:", data);

        if (data.features && data.features.length > 0) {
          const coordinates = data.features[0].geometry.coordinates;
          latInput.value = coordinates[1];
          lngInput.value = coordinates[0];

          console.log("Alınan koordinatlar:", latInput.value, lngInput.value);

          // Form verilerini konsola yazdır
          logFormData();

          try {
            // Formu gönder
            const formData = new FormData(helpForm);
            console.log("Sending form data:", Object.fromEntries(formData));

            const submitResponse = await fetch(helpForm.action, {
              method: 'POST',
              body: formData,
              headers: {
                'Accept': 'application/json'
              }
            });

            console.log("Response status:", submitResponse.status);
            console.log("Response headers:", Object.fromEntries(submitResponse.headers));

            if (!submitResponse.ok) {
              const errorText = await submitResponse.text();
              console.error("Server response:", errorText);
              throw new Error(`HTTP error! status: ${submitResponse.status}`);
            }

            const contentType = submitResponse.headers.get("content-type");
            console.log("Content-Type:", contentType);

            if (!contentType || !contentType.includes("application/json")) {
              const responseText = await submitResponse.text();
              console.error("Invalid response:", responseText);
              throw new Error("Sunucudan geçersiz yanıt alındı!");
            }

            const result = await submitResponse.json();
            console.log("Server response:", result);

            if (result.success) {
              window.location.href = result.redirect_url;
            } else {
              throw new Error(result.message || 'Form gönderimi başarısız oldu');
            }
          } catch (error) {
            console.error("Form submission error:", error);
            alert(error.message || "Form gönderilirken bir hata oluştu. Lütfen tekrar deneyin.");
          }
        } else {
          console.error("API yanıtında konum bulunamadı:", data);
          alert("Konum bulunamadı. Lütfen adres bilgilerini kontrol edin.");
          return;
        }
      } catch (error) {
        console.error("Konum alınırken hata:", error);
        alert("Konum bilgisi alınamadı. Lütfen tekrar deneyin.");
        return;
      }
    } else {
      // Konum zaten var, formu gönder
      logFormData();
      const formData = new FormData(helpForm);
      fetch(helpForm.action, {
        method: 'POST',
        body: formData,
        headers: {
          'Accept': 'application/json'
        }
      })
        .then(response => response.json())
        .then(result => {
          if (result.success) {
            window.location.href = result.redirect_url;
          } else {
            throw new Error(result.message || 'Form gönderimi başarısız oldu');
          }
        })
        .catch(error => {
          console.error('Form gönderimi sırasında hata:', error);
          alert('Form gönderimi sırasında bir hata oluştu. Lütfen tekrar deneyin.');
        });
    }
  });
  // Form verilerini konsola yazdır
  function logFormData() {
    console.log("Form gönderilecek veriler:", {
      disasterType: disasterType.value,
      lat: latInput.value,
      lng: lngInput.value,
      province: provinceSelect.value,
      district: districtSelect.value,
      neighborhood: neighborhoodSelect.value,
      street: streetSelect.value,
      additional_info: document.getElementById("additional_info")?.value || "",
    });
  }

  async function loadStreets(neighborhoodId) {
    try {
      const response = await fetch(`/api/streets/${neighborhoodId}`);
      const data = await response.json();

      // Verileri alfabetik sırala
      data.sort((a, b) => a.street_name.localeCompare(b.street_name, 'tr'));

      const streetSelect = document.getElementById("street");
      streetSelect.innerHTML = '<option value="">Sokak Seçiniz</option>';

      // DocumentFragment kullanarak DOM manipülasyonunu optimize et
      const fragment = document.createDocumentFragment();

      data.forEach((street) => {
        const option = document.createElement("option");
        option.value = street.street_id;
        option.textContent = street.street_name;
        fragment.appendChild(option);
      });

      streetSelect.appendChild(fragment);
    } catch (error) {
      console.error("Sokaklar yüklenirken hata oluştu:", error);
    }
  }
});
