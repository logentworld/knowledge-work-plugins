import java.util.Properties
import org.jetbrains.kotlin.gradle.dsl.JvmTarget

abstract class CopyPluginAssets : DefaultTask() {
    @get:InputDirectory abstract val input: DirectoryProperty
    @get:OutputDirectory abstract val output: DirectoryProperty

    @TaskAction
    fun copyAssets() {
        val target = output.get().asFile
        target.deleteRecursively()
        project.copy {
            from(input)
            into(target)
        }
    }
}

plugins {
    id("com.android.library")
    id("org.jetbrains.kotlin.android")
}
val pluginRepository = projectDir.parentFile
val pluginVersion = pluginRepository.resolve("VERSION").readText().trim()
version = pluginVersion
val apiPin = Properties().apply {
    pluginRepository.resolve("plugin-api.lock").inputStream().use { load(it) }
}
android {
    namespace = "com.sleepysoong.logent.knowledgework"
    compileSdk = 37
    defaultConfig {
        minSdk = 26
        buildConfigField("String", "PLUGIN_VERSION", "\"$pluginVersion\"")
    }
    buildFeatures { buildConfig = true }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}
// 원본 트리에서 만든 같은 자산을 테스트·AAR·원본 ZIP에 사용해요.
val stagedAssets = tasks.register<Exec>("stagePluginAssets") {
    workingDir(pluginRepository)
    commandLine("python3", "logent/stage-assets.py", "--output", layout.buildDirectory.dir("staged/pluginAssets").get().asFile.absolutePath)
    outputs.dir(layout.buildDirectory.dir("staged/pluginAssets"))
    outputs.upToDateWhen { false }
}
val variantAssets = tasks.register<CopyPluginAssets>("stageVariantAssets") {
    dependsOn(stagedAssets)
    input.set(layout.buildDirectory.dir("staged/pluginAssets/assets"))
    output.set(layout.buildDirectory.dir("generated/pluginAssets"))
}
androidComponents {
    onVariants(selector().all()) { variant ->
        variant.sources.assets?.addGeneratedSourceDirectory(variantAssets) { it.output }
    }
}
kotlin { compilerOptions { jvmTarget.set(JvmTarget.JVM_17) } }
kotlin.sourceSets.getByName("main").kotlin.srcDir(layout.buildDirectory.dir("staged/pluginAssets/kotlin"))
tasks.named("preBuild") { dependsOn(stagedAssets) }
apply(from = pluginRepository.resolve("logent/artifacts.gradle.kts"))
dependencies {
    // API와 코어 공유 라이브러리는 DEX에 다시 넣지 않아요.
    val api = "${apiPin.getProperty("group")}:${apiPin.getProperty("artifact")}:${apiPin.getProperty("version")}"
    compileOnly(api)
    testImplementation(api)
    testImplementation("junit:junit:4.13.2")
}
tasks.withType<Test>().configureEach {
    dependsOn(stagedAssets)
    systemProperty("logent.plugin.assets", layout.buildDirectory.dir("staged/pluginAssets/assets").get().asFile.absolutePath)
    systemProperty("logent.knowledgework.assets", layout.buildDirectory.dir("staged/pluginAssets/assets/plugins/knowledge-work").get().asFile.absolutePath)
}
