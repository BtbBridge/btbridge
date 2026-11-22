import java.io.File

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

android {
    namespace = "com.btbridge.app"
    compileSdk = 35
    buildToolsVersion = "35.0.0"

    defaultConfig {
        applicationId = "com.btbridge.app"
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "1.0.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    buildFeatures {
        compose = true
    }
}

dependencies {
    implementation(platform("androidx.compose:compose-bom:2024.12.01"))
    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.7")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.8.7")
    implementation("androidx.activity:activity-compose:1.9.3")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-graphics")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material:material-icons-extended")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.9.0")

    testImplementation("junit:junit:4.13.2")
    debugImplementation("androidx.compose.ui:ui-tooling")
}

tasks.withType<Test>().configureEach {
    doFirst {
        val osName = System.getProperty("os.name").orEmpty().lowercase()
        val hasNonAscii = classpath.files.any { f -> f.absolutePath.any { it.code > 127 } } ||
            testClassesDirs.files.any { f -> f.absolutePath.any { it.code > 127 } }
        if (osName.contains("win") && hasNonAscii) {
            val anchor = rootProject.rootDir.parentFile ?: rootProject.rootDir
            val proc = ProcessBuilder("cmd", "/c", "for %I in (\"${anchor.absolutePath}\") do @echo %~sI")
                .redirectErrorStream(true)
                .start()
            val shortAnchor = proc.inputStream.bufferedReader().readText().trim()
            if (proc.waitFor() == 0 && shortAnchor.isNotEmpty() && shortAnchor.all { it.code <= 127 }) {
                val longPrefix = anchor.absolutePath
                val remap: (File) -> File = { f ->
                    val p = f.absolutePath
                    if (p.startsWith(longPrefix)) File(shortAnchor + p.removePrefix(longPrefix)) else f
                }
                testClassesDirs = files(testClassesDirs.files.map(remap))
                classpath = files(classpath.files.map(remap))
            }
        }
    }
}
