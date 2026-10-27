#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "RebirthMaterialDiagnosticsLibrary.generated.h"

class UMaterialInterface;

UCLASS()
class REBIRTHMATERIALPREVIEW_API URebirthMaterialDiagnosticsLibrary : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()

public:
    /** Check already-loaded material state without loading, compiling, or submitting it to the renderer. */
    UFUNCTION(BlueprintCallable, Category = "Rebirth|Material Diagnostics")
    static FString GetMaterialPreviewPreflight(UMaterialInterface* Material);

    /** Read actual current-RHI material resources without reconstructing or editing graphs.
     * Optional waiting only finishes compilation jobs which already exist.
     * Python: unreal.RebirthMaterialDiagnosticsLibrary.get_material_diagnostics(material, False)
     */
    UFUNCTION(BlueprintCallable, Category = "Rebirth|Material Diagnostics")
    static FString GetMaterialDiagnostics(UMaterialInterface* Material, bool bWaitForCompilation = false);

    /** Inspect a loaded object without creating its native asset editor, compiling
     * Blueprint graphs, constructing gameplay instances, or following references.
     */
    UFUNCTION(BlueprintCallable, Category = "Rebirth|Cooked Asset Diagnostics")
    static FString GetAssetDiagnostics(UObject* Asset);

    /** Explicitly load an asset and inspect it. A phase JSON is flushed under
     * Saved/RebirthMaterialPreview/Diagnostics before native LoadObject starts.
     * A loader failure can still crash the process; this is diagnostic evidence,
     * not a crash recovery mechanism or gameplay execution test.
     */
    UFUNCTION(BlueprintCallable, Category = "Rebirth|Cooked Asset Diagnostics")
    static FString LoadAssetDiagnostics(const FString& ObjectPath);

    /** Draw the active level-editor viewport and synchronously save its actual
     * pixels to an absolute PNG filename. Requires an initialized rendering
     * editor on the game thread; it does not create a SceneCapture actor or
     * change scene assets. Python returns a JSON receipt, including failures.
     */
    UFUNCTION(BlueprintCallable, Category = "Rebirth|Preview Capture")
    static FString CaptureEditorViewportImage(const FString& Filename, bool bUsePilotedCameraSettings = false);
};
